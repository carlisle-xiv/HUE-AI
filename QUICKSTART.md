# Quick Start Guide - Health Assistant

Get your AI Health Assistant up and running in 5 steps!

## Prerequisites

- Python 3.9+
- PostgreSQL database
- 16GB+ RAM (32GB recommended)
- 20GB free disk space
- Optional: NVIDIA GPU with CUDA (for faster inference)

## Step 1: Install Dependencies ⚙️

```bash
pip install -r requirements.txt
```

**Packages installed:**
- FastAPI, SQLModel, PostgreSQL drivers
- PyTorch, Transformers, bitsandbytes
- Image processing libraries

## Step 2: Configure Database 🗄️

Create your `.env` file in the project root:

```bash
# Copy this content to .env
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hue_ai_db

APP_NAME=HUE-AI
DEBUG=True
```

## Step 3: Run Migrations 🔧

```bash
alembic upgrade head
```

This creates the necessary database tables:
- `health_sessions` - Conversation sessions
- `health_messages` - Chat messages

## Step 4: Start the Server 🚀

```bash
python main.py
```

**What happens on first startup:**
1. FastAPI application initializes (2-3 seconds)
2. AI models download from HuggingFace (~10GB, 5-10 minutes) ⏳
3. Models load into memory (30 seconds)
4. Server ready! ✅

**Subsequent startups:** Only step 1 and 3 (~45 seconds total)

**Expected logs:**
```
INFO:     Starting HUE-AI application...
INFO:     Loading AI models (this may take a few minutes)...
INFO:     Loading BioMistral-7B model...
INFO:     BioMistral-7B loaded successfully!
INFO:     Loading LLaVA-v1.6-mistral-7b model...
INFO:     LLaVA-v1.6-mistral-7b loaded successfully!
INFO:     ✓ All AI models loaded successfully!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 5: Test It! 🧪

### Option A: Interactive API Docs
Visit http://localhost:8000/docs

### Option B: Command Line (curl)
```bash
# Check health
curl http://localhost:8000/api/v1/health-assistant/health

# Send a medical query
curl -X POST http://localhost:8000/api/v1/health-assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "I have been experiencing headaches for 3 days",
    "user_id": "test_user"
  }'
```

### Option C: Automated Test Suite
```bash
python test_health_assistant.py
```

## 🎯 Your First Conversation

### 1. Start a new conversation (text-only)
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/health-assistant/chat",
    json={
        "prompt": "I've been feeling tired and dizzy lately. What could cause this?",
        "user_id": "user123"
    }
)

data = response.json()
print(f"AI Response: {data['response']}")
print(f"Session ID: {data['session_id']}")  # Save this!
```

**Response:**
- Uses **BioMistral-7B** model
- Takes 2-10 seconds (GPU) or 10-30 seconds (CPU)
- Creates a new session automatically

### 2. Continue the conversation
```python
response = requests.post(
    "http://localhost:8000/api/v1/health-assistant/chat",
    json={
        "prompt": "Should I see a doctor?",
        "session_id": data['session_id'],  # Use saved session_id
        "user_id": "user123"
    }
)

print(response.json()['response'])
```

**Response:**
- Remembers previous conversation
- Provides contextual advice

### 3. Analyze a medical image
```python
import base64

# Read and encode image
with open("medical_image.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:8000/api/v1/health-assistant/chat",
    json={
        "prompt": "What do you see in this image?",
        "image_base64": image_b64,
        "user_id": "user123"
    }
)

data = response.json()
print(f"Model used: {data['model_used']}")  # llava-v1.6-mistral-7b
print(f"Analysis: {data['response']}")
```

**Response:**
- Uses **LLaVA-v1.6** model
- Takes 5-15 seconds (GPU) or 30-60 seconds (CPU)
- Analyzes image content

## 📊 Available Endpoints

| Endpoint | Method | Purpose | Example |
|----------|--------|---------|---------|
| `/health` | GET | Check models ready | Health check |
| `/chat` | POST | Send message (JSON) | Text or image query |
| `/chat/upload` | POST | Send with file | File upload |
| `/sessions` | GET | List sessions | User history |
| `/sessions/{id}` | GET | Get conversation | Full chat history |
| `/sessions/{id}` | DELETE | End session | Close chat |

All endpoints are under: `http://localhost:8000/api/v1/health-assistant/`

## 🔍 Troubleshooting

### "Models not loading"
**Symptoms:** Health check shows models not ready
**Solutions:**
- Check internet connection (first startup downloads ~10GB)
- Verify 20GB free disk space
- Check logs for specific error messages
- For GPU: Verify CUDA installation with `nvidia-smi`

### "Out of memory"
**Symptoms:** CUDA OOM or system RAM exhausted
**Solutions:**
- Close other applications
- Reduce `max_tokens` in requests (try 256 instead of 512)
- Use CPU mode (automatic fallback)

### "Slow responses"
**Symptoms:** >30 seconds per response
**Solutions:**
- Check if GPU is being used (logs show "cuda" or "cpu")
- Install CUDA toolkit for GPU acceleration
- Reduce `temperature` and `max_tokens`
- This is normal for CPU-only mode

### "Cannot connect to database"
**Symptoms:** Database connection errors
**Solutions:**
- Verify PostgreSQL is running: `pg_isready`
- Check `.env` credentials match your PostgreSQL setup
- Ensure database exists: `createdb hue_ai_db`
- Run migrations: `alembic upgrade head`

## 📚 Next Steps

1. **Read the full guide**: `HEALTH_ASSISTANT_GUIDE.md`
2. **Review implementation**: `IMPLEMENTATION_SUMMARY.md`
3. **Explore API docs**: http://localhost:8000/docs
4. **Run tests**: `python test_health_assistant.py`
5. **Build frontend**: Connect to the API endpoints

## ⚡ Quick Reference

### Start Server
```bash
python main.py
```

### Run Tests
```bash
python test_health_assistant.py
```

### Check Logs
```bash
# Server logs show in terminal
# Look for: model loading status, inference times, errors
```

### Reset Database
```bash
alembic downgrade -1  # Rollback one migration
alembic upgrade head   # Apply again
```

### Example cURL Commands
```bash
# Health check
curl http://localhost:8000/api/v1/health-assistant/health

# Text query
curl -X POST http://localhost:8000/api/v1/health-assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "I have a headache", "user_id": "user123"}'

# Get sessions
curl "http://localhost:8000/api/v1/health-assistant/sessions?user_id=user123"
```

## 🎉 You're Ready!

Your AI Health Assistant is now running with:
- ✅ BioMistral-7B for medical conversations
- ✅ LLaVA-v1.6 for image analysis
- ✅ Session management for context
- ✅ PostgreSQL for data persistence
- ✅ RESTful API with comprehensive endpoints

**Start chatting with your AI health assistant!** 🏥🤖

---

**Need help?** Check the troubleshooting section or review the full guides:
- `HEALTH_ASSISTANT_GUIDE.md` - Complete API documentation
- `IMPLEMENTATION_SUMMARY.md` - Architecture details
- `README.md` - General project information

