import asyncio
import json
import logging
from typing import AsyncGenerator, Optional, Callable, Any
from dataclasses import dataclass

import httpx

from .config import (
    SPEECHMATICS_API_KEY,
    SPEECHMATICS_RT_URL,
    DEFAULT_LANGUAGE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_AUDIO_FORMAT,
)
from .schemas import TranscriptionResult, TranscriptionWord

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class STTSession:
    """Represents an active STT session configuration"""
    language: str = DEFAULT_LANGUAGE
    sample_rate: int = DEFAULT_SAMPLE_RATE
    audio_format: str = DEFAULT_AUDIO_FORMAT
    enable_partials: bool = True


class SpeechmaticsSTTService:
    """
    Service for real-time speech-to-text using Speechmatics API.
    
    This service manages WebSocket connections to Speechmatics and handles
    the bidirectional communication for audio streaming and transcription.
    """
    
    def __init__(self, api_key: str = SPEECHMATICS_API_KEY):
        """
        Initialize the STT service.
        
        Args:
            api_key: Speechmatics API key
        """
        self.api_key = api_key
        self.base_url = SPEECHMATICS_RT_URL
        self._is_connected = False
        self._session_id: Optional[str] = None
        
    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_key)
    
    async def get_temp_token(self) -> Optional[str]:
        """
        Get a temporary authentication token from Speechmatics.
        
        The temp token is used for WebSocket authentication and is valid
        for a limited time.
        
        Returns:
            Temporary token string or None if failed
        """
        if not self.api_key:
            logger.error("No API key configured for Speechmatics")
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://mp.speechmatics.com/v1/api_keys",
                    params={"type": "rt"},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={"ttl": 3600}  # 1 hour TTL
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("key_value")
                else:
                    logger.error(f"Failed to get temp token: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting temp token: {str(e)}")
            return None
    
    def build_start_recognition_message(self, session: STTSession) -> dict:
        """
        Build the StartRecognition message for Speechmatics.
        
        Args:
            session: STT session configuration
            
        Returns:
            StartRecognition message dict
        """
        return {
            "message": "StartRecognition",
            "transcription_config": {
                "language": session.language,
                "enable_partials": session.enable_partials,
                "max_delay": 2.0,  # Maximum delay before forcing final result
                "operating_point": "enhanced",  # Use enhanced accuracy model
            },
            "audio_format": {
                "type": "raw",
                "encoding": session.audio_format,
                "sample_rate": session.sample_rate,
            }
        }
    
    def parse_transcript_message(self, message: dict) -> Optional[TranscriptionResult]:
        """
        Parse a transcript message from Speechmatics.
        
        Args:
            message: Raw message from Speechmatics WebSocket
            
        Returns:
            TranscriptionResult or None if not a transcript message
        """
        msg_type = message.get("message")
        
        if msg_type == "AddPartialTranscript":
            # Partial (interim) result
            transcript = message.get("metadata", {}).get("transcript", "")
            if not transcript:
                # Try alternative location
                results = message.get("results", [])
                if results:
                    transcript = " ".join(
                        alt.get("content", "")
                        for result in results
                        for alt in result.get("alternatives", [])
                    )
            
            return TranscriptionResult(
                type="partial",
                transcript=transcript,
                words=None,
                start_time=message.get("metadata", {}).get("start_time"),
                end_time=message.get("metadata", {}).get("end_time"),
            )
            
        elif msg_type == "AddTranscript":
            # Final result
            results = message.get("results", [])
            transcript_parts = []
            words = []
            
            for result in results:
                for alt in result.get("alternatives", []):
                    content = alt.get("content", "")
                    transcript_parts.append(content)
                    
                    # Extract word-level details
                    if content:
                        words.append(TranscriptionWord(
                            content=content,
                            start_time=result.get("start_time", 0),
                            end_time=result.get("end_time", 0),
                            confidence=alt.get("confidence")
                        ))
            
            transcript = " ".join(transcript_parts)
            
            return TranscriptionResult(
                type="final",
                transcript=transcript,
                words=words if words else None,
                start_time=message.get("metadata", {}).get("start_time"),
                end_time=message.get("metadata", {}).get("end_time"),
            )
            
        return None
    
    async def create_websocket_url(self, session: STTSession) -> Optional[str]:
        """
        Create the WebSocket URL with authentication.
        
        Args:
            session: STT session configuration
            
        Returns:
            WebSocket URL with auth token or None if failed
        """
        # For Speechmatics, we use the API key directly in the URL
        # or get a temporary token
        if not self.api_key:
            return None
            
        # Build URL with language parameter
        url = f"{self.base_url}/{session.language}"
        return url
    
    def get_auth_headers(self) -> dict:
        """
        Get authentication headers for WebSocket connection.
        
        Returns:
            Headers dict with authorization
        """
        return {
            "Authorization": f"Bearer {self.api_key}"
        }


# Global service instance
_stt_service: Optional[SpeechmaticsSTTService] = None


def get_stt_service() -> SpeechmaticsSTTService:
    """
    Get the global STT service instance.
    
    Returns:
        SpeechmaticsSTTService instance
    """
    global _stt_service
    if _stt_service is None:
        _stt_service = SpeechmaticsSTTService()
    return _stt_service


async def process_audio_stream(
    audio_generator: AsyncGenerator[bytes, None],
    session: STTSession,
    on_transcript: Callable[[TranscriptionResult], Any]
) -> None:
    """
    Process an audio stream through Speechmatics STT.
    
    This is a high-level function that handles the full transcription pipeline.
    
    Args:
        audio_generator: Async generator yielding audio chunks
        session: STT session configuration
        on_transcript: Callback for transcription results
    """
    import websockets
    
    service = get_stt_service()
    
    if not service.is_configured:
        logger.error("STT service not configured - missing API key")
        return
    
    url = await service.create_websocket_url(session)
    if not url:
        logger.error("Failed to create WebSocket URL")
        return
    
    headers = service.get_auth_headers()
    
    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            # Send StartRecognition message
            start_msg = service.build_start_recognition_message(session)
            await ws.send(json.dumps(start_msg))
            logger.info(f"Sent StartRecognition for language: {session.language}")
            
            # Wait for RecognitionStarted
            response = await ws.recv()
            response_data = json.loads(response)
            
            if response_data.get("message") != "RecognitionStarted":
                logger.error(f"Unexpected response: {response_data}")
                return
                
            logger.info("Recognition started successfully")
            
            # Create tasks for sending audio and receiving transcripts
            async def send_audio():
                try:
                    async for chunk in audio_generator:
                        await ws.send(chunk)
                    # Send EndOfStream
                    await ws.send(json.dumps({"message": "EndOfStream"}))
                    logger.info("Sent EndOfStream")
                except Exception as e:
                    logger.error(f"Error sending audio: {str(e)}")
            
            async def receive_transcripts():
                try:
                    async for message in ws:
                        if isinstance(message, str):
                            data = json.loads(message)
                            
                            # Check for end of transcript
                            if data.get("message") == "EndOfTranscript":
                                logger.info("Received EndOfTranscript")
                                break
                            
                            # Parse transcript messages
                            result = service.parse_transcript_message(data)
                            if result:
                                await on_transcript(result)
                                
                except Exception as e:
                    logger.error(f"Error receiving transcripts: {str(e)}")
            
            # Run both tasks concurrently
            await asyncio.gather(send_audio(), receive_transcripts())
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        raise

