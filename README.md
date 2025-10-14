# HUE-AI

AI-powered health and wellness assistant platform built with FastAPI and Hugging Face models.

## Features

### Health Assistant
AI-powered conversational health assistant that helps users:
- Describe symptoms in natural language
- Get AI suggestions for possible conditions
- Receive guidance on whether to see a doctor
- Support for both text and image-based consultations

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
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/hue_ai_db

# Hugging Face Models
HF_TEXT_MODEL=your-text-model-name
HF_IMAGE_MODEL=your-image-model-name
HF_TOKEN=your-huggingface-token

# Application Settings
APP_NAME=HUE-AI
DEBUG=True
```

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

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

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

## Development

### Adding a New Feature

1. Create a new folder in `src/` (e.g., `src/new_feature/`)
2. Add `models.py`, `schemas.py`, and `router.py`
3. Import the models in `src/models.py`
4. Include the router in `src/router.py`
5. Generate and run migrations

## License

[Your License Here]

