import logging
from typing import AsyncGenerator, Optional

import httpx

from .config import (
    SPEECHMATICS_API_KEY,
    SPEECHMATICS_TTS_URL,
    TTS_VOICES,
    DEFAULT_VOICE,
    get_voice_by_id,
)

# Configure logging
logger = logging.getLogger(__name__)


class SpeechmaticsTTSService:
    """
    Service for text-to-speech using Speechmatics TTS API.
    
    This service handles HTTP requests to Speechmatics TTS endpoint
    and provides streaming audio response.
    """
    
    def __init__(self, api_key: str = SPEECHMATICS_API_KEY):
        """
        Initialize the TTS service.
        
        Args:
            api_key: Speechmatics API key
        """
        self.api_key = api_key
        self.base_url = SPEECHMATICS_TTS_URL
        
    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_key)
    
    def get_available_voices(self) -> list:
        """
        Get list of available TTS voices.
        
        Returns:
            List of voice configuration dicts
        """
        return TTS_VOICES.copy()
    
    def validate_voice(self, voice_id: str) -> bool:
        """
        Check if a voice ID is valid.
        
        Args:
            voice_id: Voice identifier to validate
            
        Returns:
            True if voice is valid, False otherwise
        """
        return get_voice_by_id(voice_id) is not None
    
    async def synthesize(
        self,
        text: str,
        voice: str = DEFAULT_VOICE
    ) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID to use
            
        Returns:
            Audio bytes (WAV format)
            
        Raises:
            ValueError: If voice is invalid or API key not configured
            httpx.HTTPError: If API request fails
        """
        if not self.is_configured:
            raise ValueError("TTS service not configured - missing API key")
            
        if not self.validate_voice(voice):
            raise ValueError(f"Invalid voice ID: {voice}. Available: {[v['id'] for v in TTS_VOICES]}")
        
        url = f"{self.base_url}/{voice}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"text": text}
            )
            
            if response.status_code != 200:
                logger.error(f"TTS API error: {response.status_code} - {response.text}")
                raise httpx.HTTPStatusError(
                    f"TTS API returned {response.status_code}",
                    request=response.request,
                    response=response
                )
            
            return response.content
    
    async def synthesize_stream(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        chunk_size: int = 8192
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech from text with streaming response.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID to use
            chunk_size: Size of audio chunks to yield
            
        Yields:
            Audio bytes chunks (WAV format)
            
        Raises:
            ValueError: If voice is invalid or API key not configured
            httpx.HTTPError: If API request fails
        """
        if not self.is_configured:
            raise ValueError("TTS service not configured - missing API key")
            
        if not self.validate_voice(voice):
            raise ValueError(f"Invalid voice ID: {voice}. Available: {[v['id'] for v in TTS_VOICES]}")
        
        url = f"{self.base_url}/{voice}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"text": text}
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"TTS API error: {response.status_code} - {error_text.decode()}")
                    raise httpx.HTTPStatusError(
                        f"TTS API returned {response.status_code}",
                        request=response.request,
                        response=response
                    )
                
                async for chunk in response.aiter_bytes(chunk_size):
                    yield chunk


# Global service instance
_tts_service: Optional[SpeechmaticsTTSService] = None


def get_tts_service() -> SpeechmaticsTTSService:
    """
    Get the global TTS service instance.
    
    Returns:
        SpeechmaticsTTSService instance
    """
    global _tts_service
    if _tts_service is None:
        _tts_service = SpeechmaticsTTSService()
    return _tts_service


async def synthesize_text(
    text: str,
    voice: str = DEFAULT_VOICE
) -> bytes:
    """
    High-level function to synthesize text to speech.
    
    Args:
        text: Text to convert to speech
        voice: Voice ID to use (default: sarah)
        
    Returns:
        Audio bytes (WAV format)
    """
    service = get_tts_service()
    return await service.synthesize(text, voice)


async def synthesize_text_stream(
    text: str,
    voice: str = DEFAULT_VOICE,
    chunk_size: int = 8192
) -> AsyncGenerator[bytes, None]:
    """
    High-level function to synthesize text to speech with streaming.
    
    Args:
        text: Text to convert to speech
        voice: Voice ID to use (default: sarah)
        chunk_size: Size of audio chunks to yield
        
    Yields:
        Audio bytes chunks (WAV format)
    """
    service = get_tts_service()
    async for chunk in service.synthesize_stream(text, voice, chunk_size):
        yield chunk

