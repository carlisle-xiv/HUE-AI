# HuggingFace Setup Guide

## Multi Disease Detector with openai/gpt-oss-120b

The Multi Disease Detector feature now uses the [openai/gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b) model via HuggingFace Inference API.

### ✅ Benefits

- **No Local GPU/RAM Required**: Model runs on HuggingFace infrastructure
- **Instant Startup**: No model loading delay
- **Always Up-to-Date**: Access latest model version
- **Cost-Effective**: Pay-per-use pricing
- **Production-Ready**: HuggingFace's robust infrastructure

---

## 🔑 Getting Your HuggingFace API Key

### Step 1: Create a HuggingFace Account
1. Go to [https://huggingface.co/join](https://huggingface.co/join)
2. Sign up with your email or GitHub account

### Step 2: Generate API Token
1. Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Click **"New token"**
3. Choose **"Read"** permission (sufficient for inference)
4. Give it a name (e.g., "HUE-AI-Multi-Disease-Detector")
5. Click **"Generate token"**
6. **Copy the token** (you won't see it again!)

### Step 3: Add to Environment Variables
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your token:
   ```bash
   HUGGINGFACE_API_KEY=hf_your_actual_token_here
   ```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd /Users/defiant-folk17/Desktop/HUE/HUE-AI
source locale/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your HUGGINGFACE_API_KEY
nano .env  # or use your preferred editor
```

### 3. Run Database Migration
```bash
alembic upgrade head
```

### 4. Start the Application
```bash
python main.py
```

The application will start instantly (no model loading required)!

---

## 📊 Model Details: openai/gpt-oss-120b

From the [official model card](https://huggingface.co/openai/gpt-oss-120b):

- **Parameters**: 117B parameters (5.1B active)
- **License**: Apache 2.0 (permissive)
- **Format**: Harmony response format (automatically applied)
- **Capabilities**:
  - Advanced reasoning with configurable effort levels
  - Full chain-of-thought access
  - Function calling and agentic tasks
  - Medical and health consultation
  - Structured outputs

### Reasoning Levels

The model supports three reasoning levels (configured in `service.py`):

- **low**: Fast responses for general dialogue
- **medium**: Balanced speed and detail (default)
- **high**: Deep and detailed analysis

---

## 🔧 Configuration Options

Edit `src/multi_disease_detector/service.py` to customize:

```python
# Line 27-31
MODEL_NAME = "openai/gpt-oss-120b"    # Model identifier
MAX_HISTORY_MESSAGES = 10              # Conversation context
MAX_RESPONSE_TOKENS = 1024             # Max response length
REASONING_LEVEL = "medium"             # low, medium, or high
```

---

## 🧪 Testing the API

### Via Swagger UI
1. Navigate to: `http://localhost:8000/docs`
2. Find "Multi Disease Detector" section
3. Try the `/api/v1/multi-disease-detector/chat` endpoint

### Via cURL
```bash
curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have been experiencing frequent headaches",
    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
    "vitals_data": {
      "blood_pressure_systolic": 130,
      "blood_pressure_diastolic": 85
    }
  }'
```

---

## 💰 Pricing

HuggingFace Inference API pricing:
- **Free tier**: Limited requests per month
- **Pay-as-you-go**: ~$0.001-0.002 per request (varies by model size)
- **Dedicated endpoints**: Fixed monthly fee for high-volume usage

Check current pricing: [https://huggingface.co/pricing](https://huggingface.co/pricing)

---

## 🐛 Troubleshooting

### "HUGGINGFACE_API_KEY is required" Error
**Solution**: Make sure you've:
1. Created a `.env` file from `.env.example`
2. Added your actual HuggingFace token
3. Restarted the application

### "Rate limit exceeded" Error
**Solution**: 
- You've hit the free tier limit
- Upgrade to pay-as-you-go on HuggingFace
- Or wait for the rate limit to reset

### "Model not found" Error
**Solution**:
- Verify you have access to `openai/gpt-oss-120b`
- Check your API token has "Read" permission
- Ensure model name is correct in `service.py`

### Slow Responses
**Note**: First request may take 10-20 seconds as HuggingFace loads the model. Subsequent requests are much faster (1-3 seconds).

---

## 📚 Additional Resources

- [openai/gpt-oss-120b Model Card](https://huggingface.co/openai/gpt-oss-120b)
- [HuggingFace Inference API Docs](https://huggingface.co/docs/api-inference/index)
- [HuggingFace Python Client Docs](https://huggingface.co/docs/huggingface_hub/guides/inference)
- [GPT-OSS GitHub Repository](https://github.com/openai/gpt-oss)

---

## ✨ What Changed from Local Model

### Before (Local Model)
- ❌ Required 40-80GB RAM/VRAM
- ❌ 5-10 minute startup time
- ❌ Needed GPU for good performance
- ❌ Large disk space for model files
- ✅ No external API dependency

### After (HuggingFace API)
- ✅ No local GPU/RAM needed
- ✅ Instant startup
- ✅ Always latest model version
- ✅ Production-grade infrastructure
- ✅ Pay-per-use (cost-effective)
- ⚠️ Requires internet connection
- ⚠️ Depends on HuggingFace availability

---

**Ready to use!** Just add your HuggingFace API key and start the application.

