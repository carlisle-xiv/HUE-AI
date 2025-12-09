import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import StreamingResponse

from .config import (
    TTS_VOICES,
    DEFAULT_VOICE,
    DEFAULT_LANGUAGE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_AUDIO_FORMAT,
    validate_config,
    get_voice_by_id,
)
from .schemas import (
    TTSSynthesizeRequest,
    TTSVoice,
    TTSVoicesResponse,
    STTConfig,
    STTSessionMessage,
    TranscriptionResult,
    STTTTSHealthResponse,
    ErrorResponse,
)
from .stt_service import get_stt_service, STTSession
from .tts_service import get_tts_service, synthesize_text_stream

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/stt-tts",
    tags=["Speech-to-Text / Text-to-Speech"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


# ===== Health Check Endpoints =====

@router.get(
    "/health",
    response_model=STTTTSHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check if the STT/TTS service is operational and properly configured."
)
async def health_check() -> STTTTSHealthResponse:
    """
    Health check endpoint for STT/TTS service.
    
    Returns:
        Service health status including STT and TTS availability
    """
    stt_service = get_stt_service()
    tts_service = get_tts_service()
    
    is_healthy = validate_config()
    
    return STTTTSHealthResponse(
        status="healthy" if is_healthy else "degraded",
        service="stt-tts",
        message="STT/TTS service is operational" if is_healthy else "Service degraded - check API key configuration",
        stt_available=stt_service.is_configured,
        tts_available=tts_service.is_configured,
    )


@router.get(
    "/",
    summary="Service Information",
    description="Get information about the STT/TTS service",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
async def service_info():
    """
    Get information about the STT/TTS service.
    
    Returns:
        Service information and capabilities
    """
    return {
        "service": "Speech-to-Text / Text-to-Speech",
        "version": "1.0.0",
        "provider": "Speechmatics",
        "description": "Real-time speech recognition and text-to-speech synthesis",
        "endpoints": {
            "WebSocket /transcribe": "Real-time audio transcription",
            "POST /synthesize": "Text-to-speech synthesis with streaming audio",
            "GET /voices": "List available TTS voices",
            "GET /health": "Service health check"
        },
        "features": {
            "stt": [
                "Real-time transcription via WebSocket",
                "Partial (interim) results",
                "Word-level timestamps",
                "Multiple language support"
            ],
            "tts": [
                "Multiple voice options",
                "Streaming audio response",
                "WAV audio format output"
            ]
        }
    }


# ===== TTS Endpoints =====

@router.get(
    "/voices",
    response_model=TTSVoicesResponse,
    status_code=status.HTTP_200_OK,
    summary="List TTS Voices",
    description="Get a list of all available text-to-speech voices."
)
async def list_voices() -> TTSVoicesResponse:
    """
    List all available TTS voices.
    
    Returns:
        List of available voices with their details
    """
    voices = [TTSVoice(**voice) for voice in TTS_VOICES]
    
    return TTSVoicesResponse(
        voices=voices,
        default_voice=DEFAULT_VOICE
    )


@router.post(
    "/synthesize",
    status_code=status.HTTP_200_OK,
    summary="Synthesize Speech",
    description="""
    Convert text to speech using Speechmatics TTS API.
    
    **Features:**
    - Multiple voice options (sarah, theo, megan, jack)
    - Streaming audio response for real-time playback
    - WAV audio format output
    
    **Usage:**
    ```python
    import requests
    
    response = requests.post(
        "http://localhost:8000/api/v1/stt-tts/synthesize",
        json={"text": "Hello world", "voice": "sarah"},
        stream=True
    )
    
    # Save audio to file
    with open("output.wav", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    ```
    
    **Voice Options:**
    - `sarah`: Professional female voice (default)
    - `theo`: Professional male voice
    - `megan`: Warm female voice
    - `jack`: Friendly male voice
    """,
    responses={
        200: {
            "description": "Audio stream",
            "content": {"audio/wav": {}}
        },
        400: {
            "description": "Invalid request",
            "model": ErrorResponse
        },
        500: {
            "description": "TTS synthesis failed",
            "model": ErrorResponse
        }
    }
)
async def synthesize_speech(request: TTSSynthesizeRequest):
    """
    Synthesize speech from text.
    
    Args:
        request: TTS synthesis request with text and voice selection
        
    Returns:
        StreamingResponse with WAV audio
    """
    tts_service = get_tts_service()
    
    if not tts_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS service not configured - missing SPEECHMATICS_API_KEY"
        )
    
    # Validate voice
    if not tts_service.validate_voice(request.voice):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid voice ID: {request.voice}. Use /voices endpoint to list available voices."
        )
    
    try:
        logger.info(f"TTS synthesis request: {len(request.text)} chars, voice={request.voice}")
        
        # Return streaming response
        return StreamingResponse(
            synthesize_text_stream(request.text, request.voice),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=speech.wav",
                "Cache-Control": "no-cache",
            }
        )
        
    except ValueError as e:
        logger.error(f"TTS validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"TTS synthesis error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synthesize speech: {str(e)}"
        )


# ===== STT WebSocket Endpoint =====

@router.websocket("/transcribe")
async def transcribe_audio(
    websocket: WebSocket,
    language: str = DEFAULT_LANGUAGE,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    audio_format: str = DEFAULT_AUDIO_FORMAT,
    enable_partials: bool = True
):
    """
    Real-time audio transcription via WebSocket.
    
    **Connection:**
    ```
    ws://localhost:8000/api/v1/stt-tts/transcribe?language=en&sample_rate=16000
    ```
    
    **Protocol:**
    1. Connect to WebSocket
    2. Receive 'ready' event confirming connection
    3. Send binary audio chunks (PCM16 format)
    4. Receive JSON transcription events:
       - `{"event": "partial", "data": {"transcript": "..."}}` - Interim results
       - `{"event": "transcript", "data": {"transcript": "...", "words": [...]}}` - Final results
    5. Send `{"event": "stop"}` or close connection to end
    
    **Audio Requirements:**
    - Format: PCM 16-bit signed little-endian (pcm_s16le)
    - Sample rate: 16000 Hz (configurable)
    - Channels: Mono
    
    **Query Parameters:**
    - `language`: Language code (default: "en")
    - `sample_rate`: Audio sample rate in Hz (default: 16000)
    - `audio_format`: Audio format (default: "pcm_s16le")
    - `enable_partials`: Enable interim results (default: true)
    """
    import websockets
    
    stt_service = get_stt_service()
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    # Check if service is configured
    if not stt_service.is_configured:
        await websocket.send_json({
            "event": "error",
            "error": "STT service not configured - missing SPEECHMATICS_API_KEY"
        })
        await websocket.close(code=1008, reason="Service not configured")
        return
    
    logger.info(f"STT WebSocket connected: language={language}, sample_rate={sample_rate}")
    
    # Create session configuration
    session = STTSession(
        language=language,
        sample_rate=sample_rate,
        audio_format=audio_format,
        enable_partials=enable_partials
    )
    
    # Get WebSocket URL and headers for Speechmatics
    url = await stt_service.create_websocket_url(session)
    if not url:
        await websocket.send_json({
            "event": "error",
            "error": "Failed to create Speechmatics connection"
        })
        await websocket.close(code=1011, reason="Service error")
        return
    
    headers = stt_service.get_auth_headers()
    
    # Notify client we're ready
    await websocket.send_json({
        "event": "ready",
        "data": {
            "language": language,
            "sample_rate": sample_rate,
            "audio_format": audio_format
        }
    })
    
    # Track connection state
    client_connected = True
    speechmatics_connected = False
    
    try:
        # Connect to Speechmatics WebSocket
        async with websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=20
        ) as sm_ws:
            speechmatics_connected = True
            
            # Send StartRecognition message
            start_msg = stt_service.build_start_recognition_message(session)
            await sm_ws.send(json.dumps(start_msg))
            
            # Wait for RecognitionStarted (skip Info messages)
            recognition_started = False
            max_attempts = 10  # Prevent infinite loop
            attempts = 0
            
            while not recognition_started and attempts < max_attempts:
                response = await sm_ws.recv()
                response_data = json.loads(response)
                msg_type = response_data.get("message")
                
                if msg_type == "RecognitionStarted":
                    recognition_started = True
                    logger.info("Speechmatics recognition started")
                elif msg_type == "Info":
                    # Informational message (e.g., concurrent session usage) - log and continue
                    info_type = response_data.get("type", "unknown")
                    logger.info(f"Speechmatics info ({info_type}): {response_data.get('reason', '')}")
                elif msg_type == "Error":
                    logger.error(f"Speechmatics error: {response_data}")
                    await websocket.send_json({
                        "event": "error",
                        "error": f"Speechmatics error: {response_data.get('reason', 'Unknown')}"
                    })
                    return
                else:
                    logger.warning(f"Unexpected Speechmatics message while waiting for start: {response_data}")
                
                attempts += 1
            
            if not recognition_started:
                logger.error("Failed to receive RecognitionStarted from Speechmatics")
                await websocket.send_json({
                    "event": "error",
                    "error": "Failed to start recognition - no response from Speechmatics"
                })
                return
            await websocket.send_json({"event": "started"})
            
            # Task to forward audio from client to Speechmatics
            async def forward_audio():
                nonlocal client_connected
                try:
                    while client_connected:
                        message = await websocket.receive()
                        
                        if message["type"] == "websocket.disconnect":
                            client_connected = False
                            break
                        
                        if "bytes" in message:
                            # Forward binary audio to Speechmatics
                            await sm_ws.send(message["bytes"])
                        
                        elif "text" in message:
                            # Handle JSON control messages from client
                            try:
                                data = json.loads(message["text"])
                                if data.get("event") == "stop":
                                    logger.info("Client requested stop")
                                    await sm_ws.send(json.dumps({"message": "EndOfStream"}))
                                    break
                            except json.JSONDecodeError:
                                pass
                    
                    # Send EndOfStream when client disconnects
                    if speechmatics_connected:
                        await sm_ws.send(json.dumps({"message": "EndOfStream"}))
                        
                except WebSocketDisconnect:
                    client_connected = False
                    logger.info("Client disconnected")
                except Exception as e:
                    logger.error(f"Error forwarding audio: {str(e)}")
                    client_connected = False
            
            # Task to forward transcripts from Speechmatics to client
            async def forward_transcripts():
                nonlocal speechmatics_connected
                try:
                    async for message in sm_ws:
                        if not client_connected:
                            break
                            
                        if isinstance(message, str):
                            data = json.loads(message)
                            msg_type = data.get("message")
                            
                            if msg_type == "EndOfTranscript":
                                logger.info("Speechmatics ended transcript")
                                await websocket.send_json({"event": "end"})
                                break
                            
                            # Parse and forward transcript
                            result = stt_service.parse_transcript_message(data)
                            if result:
                                event_type = "partial" if result.type == "partial" else "transcript"
                                await websocket.send_json({
                                    "event": event_type,
                                    "data": result.model_dump()
                                })
                            
                            # Forward warnings/errors
                            if msg_type == "Warning":
                                await websocket.send_json({
                                    "event": "warning",
                                    "data": {"message": data.get("reason", "Unknown warning")}
                                })
                            elif msg_type == "Error":
                                await websocket.send_json({
                                    "event": "error",
                                    "error": data.get("reason", "Unknown error")
                                })
                                break
                                
                except Exception as e:
                    logger.error(f"Error forwarding transcripts: {str(e)}")
                finally:
                    speechmatics_connected = False
            
            # Run both tasks concurrently
            await asyncio.gather(
                forward_audio(),
                forward_transcripts(),
                return_exceptions=True
            )
            
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"Speechmatics connection failed: {e}")
        if client_connected:
            await websocket.send_json({
                "event": "error",
                "error": f"Failed to connect to Speechmatics: {str(e)}"
            })
    except Exception as e:
        logger.error(f"STT WebSocket error: {str(e)}")
        if client_connected:
            try:
                await websocket.send_json({
                    "event": "error",
                    "error": str(e)
                })
            except:
                pass
    finally:
        logger.info("STT WebSocket session ended")
        if client_connected:
            try:
                await websocket.close()
            except:
                pass

