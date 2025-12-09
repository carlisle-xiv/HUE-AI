from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ===== TTS Schemas =====

class TTSSynthesizeRequest(BaseModel):
    """Request for text-to-speech synthesis"""
    
    text: str = Field(
        ...,
        description="Text to convert to speech",
        min_length=1,
        max_length=5000
    )
    voice: str = Field(
        default="sarah",
        description="Voice ID to use (sarah, theo, megan, jack)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello, welcome to the HUE health assistant.",
                "voice": "sarah"
            }
        }


class TTSVoice(BaseModel):
    """TTS voice information"""
    
    id: str = Field(..., description="Voice identifier")
    name: str = Field(..., description="Voice display name")
    language: str = Field(..., description="Voice language code")
    gender: str = Field(..., description="Voice gender")
    description: str = Field(..., description="Voice description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sarah",
                "name": "Sarah",
                "language": "en",
                "gender": "female",
                "description": "Professional female voice"
            }
        }


class TTSVoicesResponse(BaseModel):
    """Response listing available TTS voices"""
    
    voices: List[TTSVoice] = Field(..., description="Available voices")
    default_voice: str = Field(..., description="Default voice ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "voices": [
                    {
                        "id": "sarah",
                        "name": "Sarah",
                        "language": "en",
                        "gender": "female",
                        "description": "Professional female voice"
                    }
                ],
                "default_voice": "sarah"
            }
        }


# ===== STT Schemas =====

class STTConfig(BaseModel):
    """Configuration for STT transcription session"""
    
    language: str = Field(
        default="en",
        description="Language code for transcription"
    )
    sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz"
    )
    audio_format: str = Field(
        default="pcm_s16le",
        description="Audio format (pcm_s16le or pcm_f32le)"
    )
    enable_partials: bool = Field(
        default=True,
        description="Enable partial/interim transcription results"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "language": "en",
                "sample_rate": 16000,
                "audio_format": "pcm_s16le",
                "enable_partials": True
            }
        }


class TranscriptionWord(BaseModel):
    """Individual word in transcription"""
    
    content: str = Field(..., description="Word content")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    confidence: Optional[float] = Field(None, description="Confidence score 0-1")


class TranscriptionResult(BaseModel):
    """Transcription result from STT"""
    
    type: Literal["partial", "final"] = Field(
        ...,
        description="Result type - partial (interim) or final"
    )
    transcript: str = Field(..., description="Transcribed text")
    words: Optional[List[TranscriptionWord]] = Field(
        None,
        description="Word-level details (for final results)"
    )
    start_time: Optional[float] = Field(
        None,
        description="Start time of this segment"
    )
    end_time: Optional[float] = Field(
        None,
        description="End time of this segment"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "final",
                "transcript": "Hello, how are you today?",
                "words": [
                    {"content": "Hello", "start_time": 0.0, "end_time": 0.5, "confidence": 0.98}
                ],
                "start_time": 0.0,
                "end_time": 2.5
            }
        }


class STTSessionMessage(BaseModel):
    """WebSocket message for STT session"""
    
    event: str = Field(..., description="Event type")
    data: Optional[dict] = Field(None, description="Event data")
    error: Optional[str] = Field(None, description="Error message if applicable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event": "transcript",
                "data": {
                    "type": "final",
                    "transcript": "Hello world"
                }
            }
        }


# ===== Health Check Schemas =====

class STTTTSHealthResponse(BaseModel):
    """Health check response for STT/TTS service"""
    
    status: str = Field(..., description="Service status")
    service: str = Field(default="stt-tts", description="Service name")
    message: str = Field(..., description="Status message")
    stt_available: bool = Field(..., description="Whether STT is configured")
    tts_available: bool = Field(..., description="Whether TTS is configured")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "stt-tts",
                "message": "STT/TTS service is operational",
                "stt_available": True,
                "tts_available": True,
                "timestamp": "2024-12-09T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response"""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid voice ID",
                "detail": "Voice 'unknown' is not available. Use /voices endpoint to list available voices.",
                "timestamp": "2024-12-09T10:30:00Z"
            }
        }

