# HUE-AI

AI-powered health and wellness assistant platform built with FastAPI and Hugging Face models.

## Features

### Health Assistant 🏥
AI-powered conversational health assistant that helps users:
- **Natural Language Symptom Analysis**: Describe symptoms in conversational language
- **Medical Image Analysis**: Upload images for AI-powered visual assessment
- **Dual AI Models**: 
  - BioMistral-7B for medical text conversations
  - LLaVA-v1.6-mistral-7b for medical image analysis
- **Session Management**: Maintains conversation context across multiple interactions
- **Smart Routing**: Automatically uses appropriate model based on input type
- **4-bit Quantization**: Memory-efficient model loading for faster inference

**Why it matters**: Reduces unnecessary hospital visits, empowers patients with quick insights, and builds trust by making the app their "first stop" for care.

## Project Structure

```
HUE-AI/
├── main.py                 # Application entry point
├── src/
│   ├── app.py             # FastAPI application setup
│   ├── database.py        # Database configuration
│   ├── models.py          # General models (imports all features)
│   ├── router.py          # General router (combines all features)
│   ├── schemas.py         # Common API schemas
│   └── health_assistant/  # Health Assistant feature
│       ├── models.py      # Session and message models
│       ├── schemas.py     # Feature-specific schemas
│       └── router.py      # Feature endpoints
├── alembic/               # Database migrations
└── requirements.txt       # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Database Configuration (PostgreSQL)
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hue_ai_db

# Application Settings
APP_NAME=HUE-AI
DEBUG=True
```

**Note**: HuggingFace models are automatically downloaded on first startup. Ensure you have:
- 15GB+ free disk space for model downloads
- Good internet connection (models are ~8-10GB total)
- Optional: NVIDIA GPU with CUDA for faster inference

### 3. Set Up Database

Run migrations to create database tables:

```bash
alembic upgrade head
```

### 4. Run the Application

```bash
# Using uvicorn directly
uvicorn main:app --reload

# Or using the main.py script
python main.py
```

The API will be available at `http://localhost:8000`

**⏱️ First Startup**: The first time you run the application, it will download AI models (~10GB). This can take 5-10 minutes depending on your internet connection. Subsequent starts will be much faster (~30 seconds for model loading).

### 5. Test the Health Assistant

```bash
# Run the test suite
python test_health_assistant.py
```

This will test all health assistant endpoints including:
- Model health check
- Text-based medical queries
- Conversation continuity
- Session management
- (Optional) Image analysis if test image is provided

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs` (Interactive API testing)
- **ReDoc**: `http://localhost:8000/redoc` (Detailed documentation)
- **Health Assistant Guide**: See `HEALTH_ASSISTANT_GUIDE.md` for comprehensive usage examples

### Quick API Examples

**Text Query:**
```bash
curl -X POST "http://localhost:8000/api/v1/health-assistant/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "I have been experiencing headaches for 3 days",
    "user_id": "user123"
  }'
```

**Check Model Status:**
```bash
curl "http://localhost:8000/api/v1/health-assistant/health"
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## Architecture

The project follows a modular feature-based architecture:

1. **Feature Folders**: Each AI feature (e.g., `health_assistant`) has its own folder in `src/` with:
   - `models.py`: Database models
   - `schemas.py`: Pydantic schemas for API validation
   - `router.py`: API endpoints

2. **General Files**: The main `src/` folder contains:
   - General models that import all feature models
   - General router that combines all feature routers
   - Common schemas used across features

3. **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations

## Hardware Requirements

### Minimum (CPU Mode)
- **CPU**: 4+ cores
- **RAM**: 16GB
- **Disk**: 20GB free space
- **Performance**: ~10-30s per response

### Recommended (GPU Mode)
- **GPU**: NVIDIA GPU with 8GB+ VRAM (RTX 3060 or better)
- **RAM**: 32GB
- **Disk**: 20GB free space
- **Performance**: ~2-5s per response

## Development

### Adding a New Feature

1. Create a new folder in `src/` (e.g., `src/new_feature/`)
2. Add `models.py`, `schemas.py`, and `router.py`
3. Import the models in `src/models.py`
4. Include the router in `src/router.py`
5. Generate and run migrations

## Troubleshooting

### Models Taking Too Long to Load
- **Issue**: First startup takes >10 minutes
- **Solution**: This is normal. Models are being downloaded from HuggingFace. Check your internet connection.

### Out of Memory Errors
- **Issue**: CUDA out of memory or RAM exhausted
- **Solution**: 
  - Close other applications
  - Reduce `max_tokens` parameter in requests
  - Use CPU mode if GPU memory is insufficient

### Models Not Loading
- **Issue**: Health check shows models not ready
- **Solution**: 
  - Check logs for specific error messages
  - Ensure sufficient disk space
  - Verify internet connection for model downloads
  - Check CUDA installation (for GPU mode)

## License

[Your License Here]

