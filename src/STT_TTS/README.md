# STT/TTS Module - Speechmatics Integration

Real-time Speech-to-Text (STT) and Text-to-Speech (TTS) services using [Speechmatics](https://www.speechmatics.com/).

## Features

### Speech-to-Text (STT)
- Real-time transcription via WebSocket
- Partial (interim) results for live feedback
- Word-level timestamps and confidence scores
- Multiple language support

### Text-to-Speech (TTS)
- Multiple voice options (sarah, theo, megan, jack)
- Streaming audio response for real-time playback
- WAV audio format output

## Setup

### 1. Install Dependencies

```bash
pip install speechmatics-python websockets
```

Or update all dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Add your Speechmatics API key to `.env`:

```env
SPEECHMATICS_API_KEY=your_api_key_here
SPEECHMATICS_RT_URL=wss://eu2.rt.speechmatics.com/v2
```

Get your API key from the [Speechmatics Portal](https://portal.speechmatics.com/).

## API Endpoints

### Health Check

```http
GET /api/v1/stt-tts/health
```

Returns service health status and configuration.

### List TTS Voices

```http
GET /api/v1/stt-tts/voices
```

Returns available TTS voices.

**Response:**
```json
{
  "voices": [
    {
      "id": "sarah",
      "name": "Sarah",
      "language": "en",
      "gender": "female",
      "description": "Professional female voice"
    },
    ...
  ],
  "default_voice": "sarah"
}
```

### Text-to-Speech Synthesis

```http
POST /api/v1/stt-tts/synthesize
```

**Request Body:**
```json
{
  "text": "Hello, welcome to the health assistant.",
  "voice": "sarah"
}
```

**Response:** Streaming WAV audio

**Voice Options:**
- `sarah` - Professional female voice (default)
- `theo` - Professional male voice
- `megan` - Warm female voice
- `jack` - Friendly male voice

### Real-time Transcription (WebSocket)

```
WebSocket /api/v1/stt-tts/transcribe
```

**Query Parameters:**
- `language` - Language code (default: "en")
- `sample_rate` - Audio sample rate in Hz (default: 16000)
- `audio_format` - Audio format (default: "pcm_s16le")
- `enable_partials` - Enable interim results (default: true)

## Usage Examples

### Python - TTS (Text-to-Speech)

```python
import requests

# Synthesize speech
response = requests.post(
    "http://localhost:8000/api/v1/stt-tts/synthesize",
    json={
        "text": "Hello, how can I help you today?",
        "voice": "sarah"
    },
    stream=True
)

# Save audio to file
with open("output.wav", "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Audio saved to output.wav")
```

### Python - STT (Speech-to-Text)

```python
import asyncio
import websockets
import json

async def transcribe_audio():
    uri = "ws://localhost:8000/api/v1/stt-tts/transcribe?language=en&sample_rate=16000"
    
    async with websockets.connect(uri) as ws:
        # Wait for ready event
        response = await ws.recv()
        data = json.loads(response)
        
        if data["event"] != "ready":
            print(f"Unexpected event: {data}")
            return
        
        print("Connected, starting transcription...")
        
        # Wait for started confirmation
        response = await ws.recv()
        data = json.loads(response)
        print(f"Status: {data['event']}")
        
        # Send audio chunks (example with file)
        with open("audio.raw", "rb") as f:
            while chunk := f.read(4096):
                await ws.send(chunk)
        
        # Signal end of audio
        await ws.send(json.dumps({"event": "stop"}))
        
        # Receive transcriptions
        while True:
            response = await ws.recv()
            data = json.loads(response)
            
            if data["event"] == "end":
                print("\nTranscription complete")
                break
            elif data["event"] == "transcript":
                print(f"Final: {data['data']['transcript']}")
            elif data["event"] == "partial":
                print(f"Partial: {data['data']['transcript']}", end="\r")

asyncio.run(transcribe_audio())
```

### JavaScript - TTS (Browser)

```javascript
async function synthesizeSpeech(text, voice = 'sarah') {
    const response = await fetch('/api/v1/stt-tts/synthesize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text, voice }),
    });
    
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.play();
}

// Usage
synthesizeSpeech('Hello, welcome to the health assistant.');
```

### JavaScript - STT (Browser with Microphone)

```javascript
async function startTranscription() {
    const ws = new WebSocket('ws://localhost:8000/api/v1/stt-tts/transcribe?language=en');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.event) {
            case 'ready':
                console.log('Ready to transcribe');
                startMicrophone(ws);
                break;
            case 'partial':
                console.log('Partial:', data.data.transcript);
                break;
            case 'transcript':
                console.log('Final:', data.data.transcript);
                break;
            case 'error':
                console.error('Error:', data.error);
                break;
        }
    };
    
    ws.onerror = (error) => console.error('WebSocket error:', error);
    ws.onclose = () => console.log('Connection closed');
}

async function startMicrophone(ws) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        // Convert to 16-bit PCM
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
            pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
        }
        ws.send(pcm16.buffer);
    };
    
    source.connect(processor);
    processor.connect(audioContext.destination);
}
```

## Audio Format Requirements

For STT transcription:
- **Format:** PCM 16-bit signed little-endian (`pcm_s16le`)
- **Sample Rate:** 16000 Hz (recommended)
- **Channels:** Mono

## Error Handling

The WebSocket sends JSON messages for all events including errors:

```json
{
    "event": "error",
    "error": "Error description here"
}
```

Common errors:
- `STT service not configured` - Missing API key
- `Invalid voice ID` - Use `/voices` endpoint to see available voices
- `Failed to connect to Speechmatics` - Network or authentication issue

## Architecture

```
src/STT_TTS/
├── __init__.py        # Module exports
├── config.py          # Configuration and constants
├── schemas.py         # Pydantic models
├── router.py          # FastAPI endpoints
├── stt_service.py     # STT WebSocket logic
├── tts_service.py     # TTS HTTP logic
└── README.md          # This file
```

## References

- [Speechmatics Documentation](https://docs.speechmatics.com/)
- [Speechmatics API Reference](https://docs.speechmatics.com/api-ref/)
- [Real-time Transcription Guide](https://docs.speechmatics.com/speech-to-text/realtime-transcription)
- [TTS Quickstart](https://docs.speechmatics.com/text-to-speech/quickstart)

