# Health Assistant API Guide

## Overview

The Health Assistant is an AI-powered medical conversation system that uses state-of-the-art models to provide medical insights and analysis. It supports both text-based queries and medical image analysis.

## Features

- **Conversational AI**: Natural language understanding for medical symptoms and queries
- **Image Analysis**: Medical image interpretation (X-rays, skin conditions, wounds, etc.)
- **Session Management**: Maintains conversation context across multiple interactions
- **Dual Model Architecture**:
  - **BioMistral-7B**: Specialized medical language model for text-based consultations
  - **LLaVA-v1.6-mistral-7b**: Vision-language model for medical image analysis
- **4-bit Quantization**: Memory-efficient model loading (~10GB total for both models)

## Architecture

### Models

1. **BioMistral-7B** (`BioMistral/BioMistral-7B`)
   - Purpose: Text-based medical conversations
   - Specialization: Medical knowledge, symptom analysis, condition suggestions
   - Use case: When only text prompt is provided

2. **LLaVA-v1.6-mistral-7b** (`llava-hf/llava-v1.6-mistral-7b-hf`)
   - Purpose: Medical image analysis with text
   - Specialization: Visual medical assessment
   - Use case: When image is provided with text prompt

### Session Management

- Each conversation has a unique `session_id` (UUID)
- Sessions automatically created on first message
- Sessions maintain conversation history for context
- Sessions can be retrieved, listed, and closed

## API Endpoints

### 1. Chat Endpoint (Main)

**POST** `/api/v1/health-assistant/chat`

Dynamic endpoint that routes to appropriate model based on input.

**Request Body:**
```json
{
  "prompt": "I have a persistent headache for 3 days",
  "session_id": "optional-uuid-here",
  "user_id": "optional-user-id",
  "image_base64": "optional-base64-encoded-image",
  "max_tokens": 512,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "session_id": "generated-or-existing-uuid",
  "message_id": "message-uuid",
  "response": "AI-generated medical response...",
  "model_used": "biomistral-7b",
  "timestamp": "2025-10-14T12:00:00",
  "has_image": false,
  "metadata": {
    "model": "BioMistral-7B",
    "temperature": 0.7,
    "max_tokens": 512
  }
}
```

### 2. Chat with File Upload

**POST** `/api/v1/health-assistant/chat/upload`

Alternative endpoint for direct file uploads (multipart/form-data).

**Form Data:**
- `prompt` (required): User's query
- `session_id` (optional): Session ID
- `user_id` (optional): User ID
- `image` (optional): Image file
- `max_tokens` (optional, default: 512)
- `temperature` (optional, default: 0.7)

### 3. List Sessions

**GET** `/api/v1/health-assistant/sessions?user_id={user_id}&active_only=true`

Get all sessions for a user.

**Query Parameters:**
- `user_id` (required): User identifier
- `active_only` (optional, default: true): Filter active sessions only

**Response:**
```json
{
  "sessions": [
    {
      "id": "session-uuid",
      "user_id": "user123",
      "is_active": true,
      "created_at": "2025-10-14T10:00:00",
      "updated_at": "2025-10-14T12:00:00",
      "ended_at": null,
      "session_metadata": null
    }
  ],
  "total": 1
}
```

### 4. Get Session with Messages

**GET** `/api/v1/health-assistant/sessions/{session_id}`

Retrieve a specific session with all conversation messages.

**Response:**
```json
{
  "session": {
    "id": "session-uuid",
    "user_id": "user123",
    "is_active": true,
    "created_at": "2025-10-14T10:00:00",
    "updated_at": "2025-10-14T12:00:00"
  },
  "messages": [
    {
      "id": "message-uuid-1",
      "session_id": "session-uuid",
      "role": "user",
      "message_type": "text",
      "content": "I have a headache",
      "created_at": "2025-10-14T10:00:00"
    },
    {
      "id": "message-uuid-2",
      "session_id": "session-uuid",
      "role": "assistant",
      "message_type": "text",
      "content": "I understand you're experiencing a headache...",
      "model_used": "biomistral-7b",
      "created_at": "2025-10-14T10:00:05"
    }
  ]
}
```

### 5. End Session

**DELETE** `/api/v1/health-assistant/sessions/{session_id}`

Close/end a session.

**Response:**
```json
{
  "id": "session-uuid",
  "user_id": "user123",
  "is_active": false,
  "ended_at": "2025-10-14T12:30:00"
}
```

### 6. Health Check

**GET** `/api/v1/health-assistant/health`

Check if AI models are loaded and ready.

**Response:**
```json
{
  "status": "healthy",
  "models": {
    "biomistral_ready": true,
    "llava_ready": true,
    "device": "cuda"
  },
  "message": "All models loaded and ready"
}
```

## Usage Examples

### Example 1: Text-Only Medical Query

```python
import requests

url = "http://localhost:8000/api/v1/health-assistant/chat"

payload = {
    "prompt": "I've been experiencing fatigue and dizziness for the past week. What could be the cause?",
    "user_id": "user123",
    "temperature": 0.7
}

response = requests.post(url, json=payload)
data = response.json()

print(f"Session ID: {data['session_id']}")
print(f"Response: {data['response']}")
print(f"Model: {data['model_used']}")
```

### Example 2: Continue Conversation

```python
# Use the session_id from previous response
payload = {
    "prompt": "Should I see a doctor about this?",
    "session_id": data['session_id'],  # From previous response
    "user_id": "user123"
}

response = requests.post(url, json=payload)
continued_data = response.json()
print(f"Response: {continued_data['response']}")
```

### Example 3: Image Analysis with Base64

```python
import base64

# Read and encode image
with open("medical_image.jpg", "rb") as image_file:
    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

payload = {
    "prompt": "What do you see in this X-ray image? Is there anything concerning?",
    "image_base64": image_base64,
    "user_id": "user123"
}

response = requests.post(url, json=payload)
image_data = response.json()

print(f"Model used: {image_data['model_used']}")  # Will be "llava-v1.6-mistral-7b"
print(f"Analysis: {image_data['response']}")
```

### Example 4: File Upload

```python
url = "http://localhost:8000/api/v1/health-assistant/chat/upload"

files = {
    'image': ('skin_condition.jpg', open('skin_condition.jpg', 'rb'), 'image/jpeg')
}

data = {
    'prompt': 'Can you analyze this skin condition?',
    'user_id': 'user123',
    'temperature': '0.7'
}

response = requests.post(url, files=files, data=data)
result = response.json()
print(result['response'])
```

### Example 5: Retrieve Conversation History

```python
session_id = "your-session-uuid"
url = f"http://localhost:8000/api/v1/health-assistant/sessions/{session_id}"

response = requests.get(url)
conversation = response.json()

print(f"Session created: {conversation['session']['created_at']}")
print(f"Total messages: {len(conversation['messages'])}")

for msg in conversation['messages']:
    role = msg['role'].upper()
    content = msg['content']
    print(f"\n{role}: {content}")
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `transformers==4.35.2`
- `torch==2.1.1`
- `bitsandbytes==0.41.3`
- `accelerate==0.25.0`
- `pillow==10.1.0`
- `sentencepiece==0.1.99`

### 2. Model Download

Models are automatically downloaded on first startup from HuggingFace Hub:
- BioMistral-7B (~4-5GB with 4-bit quantization)
- LLaVA-v1.6-mistral-7b (~4-5GB with 4-bit quantization)

**Note**: First startup will take 5-10 minutes for model downloads and initialization.

### 3. Hardware Requirements

**Minimum:**
- RAM: 16GB
- GPU: NVIDIA GPU with 8GB VRAM (recommended)
- Disk: 15GB free space

**Recommended:**
- RAM: 32GB
- GPU: NVIDIA GPU with 12GB+ VRAM
- Disk: 20GB free space

**CPU-only mode**: Works but significantly slower (~10-30s per response vs 2-5s with GPU)

### 4. Run the Application

```bash
# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the main.py directly
python main.py
```

Access API docs at: `http://localhost:8000/docs`

## Model Behavior

### BioMistral Features
- Medical knowledge base trained on clinical literature
- Symptom analysis and condition suggestions
- Treatment recommendations with disclaimers
- Medication information
- Risk assessment and urgency evaluation

### LLaVA Features
- Medical image interpretation
- Visual symptom assessment
- Anatomical structure identification
- Abnormality detection
- Comparative analysis with normal conditions

## Safety & Disclaimers

**Important**: The AI assistant is designed to provide information and insights, but:

1. ✓ **Always includes medical disclaimers**
2. ✓ **Encourages consulting healthcare professionals**
3. ✓ **Flags emergency symptoms for immediate attention**
4. ✗ **Not a substitute for professional medical advice**
5. ✗ **Cannot diagnose medical conditions**
6. ✗ **Should not be used for emergency situations**

## Performance Optimization

### Response Time
- Text queries: ~2-10 seconds (GPU) / 10-30 seconds (CPU)
- Image analysis: ~5-15 seconds (GPU) / 30-60 seconds (CPU)
- First request: +2-5 seconds (model warm-up)

### Memory Management
- Models loaded once at startup (singleton pattern)
- 4-bit quantization reduces memory by 70%
- Conversation history limited to last 10 messages for context

### Concurrent Requests
- Models support sequential inference only
- Consider implementing request queue for high traffic
- Each inference locks the model temporarily

## Troubleshooting

### Models Not Loading
```
Error: Failed to load AI models
Solution: 
- Ensure sufficient disk space for model downloads
- Check internet connection
- Verify CUDA installation (for GPU support)
- Try CPU-only mode if GPU errors persist
```

### Out of Memory Errors
```
Error: CUDA out of memory
Solution:
- Reduce max_tokens parameter
- Close other GPU-intensive applications
- Use CPU mode if GPU memory insufficient
- Consider 8-bit quantization for even lower memory
```

### Slow Response Times
```
Issue: Responses taking >30 seconds
Solution:
- Verify GPU is being used (check logs for "cuda" device)
- Install CUDA toolkit if using NVIDIA GPU
- Reduce temperature and max_tokens for faster sampling
- Consider using smaller models for testing
```

## Future Enhancements

- [ ] Streaming responses for real-time feedback
- [ ] Multi-turn diagnosis flow with structured questions
- [ ] Integration with medical ontologies (SNOMED, ICD-10)
- [ ] Confidence scoring and uncertainty quantification
- [ ] Medical literature citation and references
- [ ] Multi-language support
- [ ] Voice input/output capabilities
- [ ] Integration with wearable health data

## API Rate Limiting

Currently no rate limiting implemented. For production:
- Implement per-user rate limiting
- Add request queuing system
- Consider caching for common queries
- Monitor model resource usage

## Security Considerations

- Validate and sanitize all user inputs
- Implement proper authentication/authorization
- Encrypt sensitive health data in transit and at rest
- Comply with HIPAA and data privacy regulations
- Log all medical conversations for audit trails
- Implement proper session expiration

## Contact & Support

For issues, questions, or contributions, please refer to the main project README or contact the development team.

---

**Version**: 1.0.0  
**Last Updated**: October 14, 2025  
**License**: [Your License]

