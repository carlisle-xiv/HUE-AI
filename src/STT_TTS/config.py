import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Speechmatics API Configuration
SPEECHMATICS_API_KEY = os.getenv("SPEECHMATICS_API_KEY", "")
SPEECHMATICS_RT_URL = os.getenv("SPEECHMATICS_RT_URL", "wss://eu2.rt.speechmatics.com/v2")

# TTS Configuration
SPEECHMATICS_TTS_URL = "https://preview.tts.speechmatics.com/generate"

# Available TTS voices
TTS_VOICES: List[dict] = [
    {
        "id": "sarah",
        "name": "Sarah",
        "language": "en",
        "gender": "female",
        "description": "Professional female voice"
    },
    {
        "id": "theo",
        "name": "Theo",
        "language": "en",
        "gender": "male",
        "description": "Professional male voice"
    },
    {
        "id": "megan",
        "name": "Megan",
        "language": "en",
        "gender": "female",
        "description": "Warm female voice"
    },
    {
        "id": "jack",
        "name": "Jack",
        "language": "en",
        "gender": "male",
        "description": "Friendly male voice"
    }
]

# Default voice
DEFAULT_VOICE = "sarah"

# STT Configuration
DEFAULT_LANGUAGE = "en"
DEFAULT_SAMPLE_RATE = 16000  # 16kHz is common for speech recognition

# Supported audio formats for STT
SUPPORTED_AUDIO_FORMATS = [
    "pcm_f32le",  # PCM 32-bit float, little-endian
    "pcm_s16le",  # PCM 16-bit signed, little-endian (most common)
]

DEFAULT_AUDIO_FORMAT = "pcm_s16le"

# Audio chunk settings
AUDIO_CHUNK_SIZE = 4096  # bytes per chunk


def validate_config() -> bool:
    """
    Validate that required configuration is present.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    if not SPEECHMATICS_API_KEY:
        return False
    return True


def get_voice_by_id(voice_id: str) -> dict | None:
    """
    Get voice configuration by ID.
    
    Args:
        voice_id: Voice identifier (e.g., 'sarah', 'theo')
        
    Returns:
        Voice configuration dict or None if not found
    """
    for voice in TTS_VOICES:
        if voice["id"] == voice_id:
            return voice
    return None

