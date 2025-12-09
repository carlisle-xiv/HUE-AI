"""
STT_TTS Module - Speechmatics Speech-to-Text and Text-to-Speech Integration

This module provides:
- Real-time speech-to-text via WebSocket
- Text-to-speech with streaming audio response

Usage:
    from src.STT_TTS import router

Endpoints:
    - WebSocket /api/v1/stt-tts/transcribe - Real-time audio transcription
    - POST /api/v1/stt-tts/synthesize - Text-to-speech synthesis
    - GET /api/v1/stt-tts/health - Service health check
    - GET /api/v1/stt-tts/voices - List available TTS voices
"""

from .router import router

__all__ = ["router"]

