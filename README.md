# HUE-AI

AI-powered health and wellness platform built with FastAPI, integrating cutting-edge AI models for comprehensive medical assistance, diagnostics, and healthcare management.

## 🌟 Features

### 1. Multi-Disease Detector 🩺

**Advanced AI medical assistant with tool calling and real-time streaming capabilities.**

#### Core Capabilities:
- **Conversational Medical Analysis**: Natural language symptom assessment
- **Real-Time Thinking Process**: Watch AI reason through medical problems via streaming
- **Intelligent Tool Calling**: AI autonomously uses tools when needed:
  - 🔍 **Web Search** (Tavily) - Access current medical guidelines and research
  - 📊 **Lab Results Explanation** - Interpret blood work and test values
  - 🏥 **Imaging Analysis** - Explain X-ray, CT, MRI findings
  - 📄 **Medical Summaries** - Generate comprehensive condition overviews
- **Professional Document Generation**: Create downloadable medical reports (HTML/PDF)
- **Session Management**: Maintains conversation context across interactions
- **Risk Assessment**: Automatic evaluation of symptom severity
- **Patient Context Awareness**: Personalized responses based on vitals, conditions, and medications

#### What Makes It Special:
- ✅ **Transparent AI Reasoning** - See how the AI thinks and what tools it uses
- ✅ **Current Medical Information** - Web search integration keeps data fresh
- ✅ **Professional Documentation** - Downloadable reports for healthcare providers
- ✅ **Enhanced Trust** - Tool visibility and thinking process build user confidence
- ✅ **Competitive Edge** - Matches and exceeds capabilities of platforms like MoreMeAI

### 2. Comprehensive Healthcare Platform 🏥

Full-featured healthcare management system with:
- **Patient & Doctor Management**: Complete profiles and specializations
- **Hospital Operations**: Bed management, department tracking
- **Appointment System**: Scheduling and consultation management
- **Prescription Management**: E-prescriptions and medication tracking
- **Pharmacy Integration**: Medicine inventory and dispensing
- **Insurance Integration**: Claims and coverage management
- **Medical Records**: Lab tests, imaging results, and clinical notes
- **Reference Data**: ICD-10 codes, CPT codes, medication database

## 📁 Project Structure

```
HUE-AI/
├── main.py                          # Application entry point
├── src/
│   ├── app.py                       # FastAPI application setup
│   ├── database.py                  # Database configuration
│   ├── router.py                    # Main router (combines all features)
│   ├── schemas.py                   # Common API schemas
│   ├── models/                      # Database models
│   │   ├── core.py                  # Users, wallets, payments
│   │   ├── patients.py              # Patient profiles and records
│   │   ├── doctors.py               # Doctor profiles and specializations
│   │   ├── hospitals.py             # Hospital and department management
│   │   ├── appointments.py          # Appointments and consultations
│   │   ├── prescriptions.py         # E-prescriptions
│   │   ├── pharmacy.py              # Pharmacy and medications
│   │   ├── insurance.py             # Insurance and claims
│   │   ├── tests.py                 # Lab tests and imaging
│   │   ├── reference.py             # Medical codes (ICD-10, CPT)
│   │   └── multi_disease_detector.py # AI chat sessions
│   └── multi_disease_detector/      # AI Medical Assistant Feature
│       ├── models.py                # Model re-exports
│       ├── schemas.py               # Request/response schemas
│       ├── service.py               # Core business logic & AI integration
│       ├── router.py                # API endpoints
│       ├── tools.py                 # Tool definitions (OpenRouter format)
│       ├── tool_service.py          # Tool execution (Tavily integration)
│       ├── artifacts.py             # Document generation & PDF conversion
│       └── README.md                # Feature documentation
├── alembic/                         # Database migrations
│   └── versions/                    # Migration files
├── requirements.txt                 # Python dependencies
├── QUICK_START.md                   # Quick setup guide
├── SETUP_NEW_FEATURES.md            # Tool calling setup
├── TOOL_CALLING_AND_STREAMING_GUIDE.md  # Comprehensive usage guide
└── test_tools_and_streaming.py     # Test suite for new features
```

## 🚀 Quick Start

**TL;DR:** See [QUICK_START.md](QUICK_START.md) for a rapid setup guide!

### 1. Prerequisites

- Python 3.11+
- PostgreSQL database
- API Keys:
  - [OpenRouter](https://openrouter.ai/) - For AI model access
  - [Tavily](https://tavily.com/) - For web search (free tier available)

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv locale
source locale/bin/activate  # On Windows: locale\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Key Dependencies:**
- `fastapi` - Web framework
- `sqlalchemy` - ORM for database
- `httpx` - Async HTTP client for OpenRouter
- `tavily-python` - Web search integration
- `weasyprint` - PDF generation (optional, requires system libraries)

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# Database Configuration (PostgreSQL)
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hue_ai_db

# AI Service API Keys
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key_here
TAVILY_API_KEY=tvly-your_tavily_key_here

# Application Settings
APP_NAME=HUE-AI
DEBUG=True
```

**Getting API Keys:**

1. **OpenRouter** (Required for AI features):
   - Sign up at [openrouter.ai](https://openrouter.ai/)
   - Navigate to API Keys section
   - Create a new key (starts with `sk-or-v1-`)

2. **Tavily** (Required for web search tool):
   - Sign up at [tavily.com](https://tavily.com/)
   - Free tier: ~1,000 searches/month
   - Copy your API key (starts with `tvly-`)

### 4. Set Up Database

```bash
# Ensure PostgreSQL is running
# Create database if it doesn't exist
createdb hue_ai_db

# Run migrations to create all tables
alembic upgrade head
```

This creates tables for:
- Users, wallets, and payments
- Patients and doctors
- Hospitals and departments
- Appointments and consultations
- Prescriptions and pharmacy
- Lab tests and imaging
- Insurance and claims
- AI chat sessions

### 5. Run the Application

```bash
# Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the main.py script
python main.py
```

The API will be available at `http://localhost:8000`

**✅ Fast Startup**: Application starts instantly using OpenRouter's API. No model downloads required!

### 6. Test the Multi-Disease Detector

```bash
# Run the comprehensive test suite
python test_tools_and_streaming.py
```

This validates:
- ✅ Tool definitions (4 tools)
- ✅ Schema validation
- ✅ Artifact generation
- ✅ HTML/PDF conversion
- ✅ Tavily web search integration
- ✅ Tool execution service

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs` (Interactive API testing)
- **ReDoc**: `http://localhost:8000/redoc` (Detailed documentation)
- **Comprehensive Guide**: See [TOOL_CALLING_AND_STREAMING_GUIDE.md](TOOL_CALLING_AND_STREAMING_GUIDE.md)

### Key Endpoints

#### Multi-Disease Detector

**Base URL:** `/api/v1/multi-disease-detector`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Basic conversational endpoint |
| `/chat/with-tools` | POST | **Enhanced chat with tool calling** |
| `/chat/stream` | POST | **Real-time streaming with thinking process** |
| `/artifacts/to-html` | POST | Convert artifact to HTML |
| `/artifacts/generate-pdf` | POST | Generate downloadable PDF |

### Quick API Examples

#### 1. Enhanced Chat with Tools

```bash
curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/chat/with-tools" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the latest treatments for high blood pressure?",
    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
    "vitals_data": {
      "blood_pressure_systolic": 145,
      "blood_pressure_diastolic": 95
    }
  }'
```

**Response includes:**
- AI's answer (using web search if needed)
- `tools_used`: ["tavily_web_search"]
- `thinking_summary`: Brief reasoning summary
- `risk_assessment`: Risk level
- Medical disclaimer

#### 2. Real-Time Streaming Chat

```bash
curl -N -X POST "http://localhost:8000/api/v1/multi-disease-detector/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain my cholesterol results: Total 240, LDL 160, HDL 35",
    "patient_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Streams events:**
- `thinking` - AI's reasoning steps
- `tool_call` - Tool being used
- `tool_result` - Tool execution results
- `content` - Response text (token by token)
- `done` - Final summary

#### 3. Basic Chat (Original)

```bash
curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have had a headache for 3 days",
    "patient_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
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

## 🏗️ Architecture

### Modular Design

The project follows a **feature-based modular architecture**:

1. **Database Models** (`src/models/`):
   - Organized by domain (core, patients, doctors, hospitals, etc.)
   - SQLAlchemy ORM with relationships
   - Alembic migrations for version control

2. **AI Features** (`src/multi_disease_detector/`):
   - Self-contained feature modules
   - Service layer for business logic
   - Tool system for extensibility
   - Artifact generation pipeline

3. **API Layer**:
   - FastAPI routers per feature
   - Pydantic schemas for validation
   - Centralized error handling
   - CORS and security middleware

4. **AI Integration**:
   - OpenRouter API for model access
   - Tool calling system (OpenRouter format)
   - Tavily API for web search
   - Streaming support (SSE)

### Tool System Architecture

```
User Request
    ↓
API Endpoint (/chat/with-tools or /chat/stream)
    ↓
Service Layer (process_chat_request_with_tools)
    ↓
AI Model with Tools (OpenRouter)
    ↓
Tool Execution (if needed)
    ├── Tavily Web Search
    ├── Lab Explanation Generator
    ├── Imaging Analysis Generator
    └── Medical Summary Generator
    ↓
AI Synthesis (with tool results)
    ↓
Response Generation + Artifacts
    ↓
User (via API or Stream)
```

## ⚙️ System Requirements

### Minimum
- **CPU**: 2+ cores
- **RAM**: 4GB
- **Disk**: 5GB free space
- **Network**: Stable internet connection
- **Performance**: 1-5s per response (depending on tools used)

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 10GB+ free space
- **Network**: High-speed internet
- **Performance**: 1-3s per response

**Note**: No GPU required! All AI processing happens via OpenRouter API.

## 🔧 Development

### Adding a New Feature

1. **Create Feature Package**:
   ```bash
   mkdir src/new_feature
   touch src/new_feature/{__init__.py,models.py,schemas.py,router.py,service.py}
   ```

2. **Define Database Models** (`models.py`):
   - Create SQLAlchemy models
   - Add relationships to existing models

3. **Add to Models Index**:
   - Create new file in `src/models/new_feature.py`
   - Import in `src/models/__init__.py`

4. **Create Schemas** (`schemas.py`):
   - Request/response Pydantic models
   - Validation rules

5. **Implement Business Logic** (`service.py`):
   - Core feature functionality
   - External API integrations

6. **Create API Endpoints** (`router.py`):
   - FastAPI router
   - Include in `src/router.py`

7. **Generate and Run Migration**:
   ```bash
   alembic revision --autogenerate -m "add new feature"
   alembic upgrade head
   ```

### Adding a New Tool

1. **Define Tool** in `src/multi_disease_detector/tools.py`:
   ```python
   {
       "type": "function",
       "function": {
           "name": "your_tool_name",
           "description": "Clear description of what the tool does",
           "parameters": {...}
       }
   }
   ```

2. **Implement Execution** in `src/multi_disease_detector/tool_service.py`:
   ```python
   async def execute_tool(tool_name: str, arguments: dict):
       if tool_name == "your_tool_name":
           # Implementation
           return result
   ```

3. **Test the Tool**:
   - Add test cases to `test_tools_and_streaming.py`
   - Test via API endpoints

### Environment Setup for Development

```bash
# Clone repository
git clone <repository-url>
cd HUE-AI

# Create virtual environment
python -m venv locale
source locale/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Run tests
python test_tools_and_streaming.py
```

## 🐛 Troubleshooting

### API Key Issues

**Issue**: "OPENROUTER_API_KEY not found" or "TAVILY_API_KEY not found"
```bash
# Check .env file exists
ls -la .env

# Verify keys are set
cat .env | grep API_KEY

# Restart application after adding keys
```

### Database Connection Errors

**Issue**: "Could not connect to PostgreSQL"
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection details in .env
psql -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_HOST

# Check database exists
psql -l | grep hue_ai_db
```

### Tool Execution Failures

**Issue**: Web search not working
- Verify Tavily API key is valid
- Check API quota (free tier: ~1,000/month)
- Review logs for specific errors
- Test Tavily directly: https://tavily.com/docs

**Issue**: PDF generation failing
```bash
# Install system dependencies
# macOS:
brew install pango cairo gdk-pixbuf libffi

# Ubuntu/Debian:
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0

# Reinstall weasyprint
pip install --force-reinstall weasyprint
```

### Streaming Disconnects

**Issue**: SSE connection drops unexpectedly
- Check nginx/proxy buffering settings
- Add header: `X-Accel-Buffering: no`
- Increase timeout settings
- Verify network stability

### Slow Response Times

**Issue**: Responses taking >10 seconds
- Check internet connection (API calls to OpenRouter/Tavily)
- Review logs for tool execution times
- Consider caching common searches
- Monitor API rate limits

## 🛠️ Technologies Used

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations
- **PostgreSQL** - Relational database
- **Pydantic** - Data validation

### AI & ML
- **OpenRouter** - AI model API (Google Gemini Flash 1.5)
- **Tavily** - Web search API for current information
- **Tool Calling** - OpenRouter function calling format

### Document Generation
- **WeasyPrint** - HTML to PDF conversion
- **Jinja2** - HTML templating

### API & Communication
- **httpx** - Async HTTP client
- **Server-Sent Events (SSE)** - Real-time streaming
- **CORS middleware** - Cross-origin support

### API References
- **OpenRouter**: https://openrouter.ai/docs
- **Tavily**: https://tavily.com/docs
- **FastAPI**: https://fastapi.tiangolo.com/

## 🎯 Use Cases

### For Patients
- 📱 Quick symptom assessment
- 📊 Understanding lab results
- 🏥 Interpreting imaging reports
- 💊 Medication information
- 🔍 Current treatment guidelines

### For Healthcare Providers
- 📄 Generate patient-friendly explanations
- 🔎 Quick reference to latest guidelines
- 📋 Pre-consultation patient insights
- 📊 Visual reports for patient education

### For Researchers
- 🧬 Medical data management
- 📈 Patient cohort tracking
- 🔬 Clinical trial coordination

## 🚀 Deployment

### Environment Variables for Production

```env
# Database (use production credentials)
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=strong_password
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
POSTGRES_DB=hue_ai_production

# API Keys (use production keys)
OPENROUTER_API_KEY=sk-or-v1-production-key
TAVILY_API_KEY=tvly-production-key

# Application
APP_NAME=HUE-AI
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com
```

### Docker Deployment (Optional)

```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    python3-cffi python3-brotli libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Use strong database passwords
- [ ] Configure HTTPS/SSL
- [ ] Set up rate limiting
- [ ] Configure monitoring (e.g., Sentry)
- [ ] Set up logging
- [ ] Configure backups
- [ ] Test disaster recovery
- [ ] Review API quotas (OpenRouter, Tavily)
- [ ] Set up CDN for static files (if any)

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Guidelines
- Follow PEP 8 style guide
- Add docstrings to functions
- Update documentation for new features
- Add tests for new functionality
- Keep PRs focused and atomic

## 📊 Performance & Costs

### API Usage Costs
- **OpenRouter**: Pay-per-use (typically $0.001-0.01 per request)
- **Tavily**: Free tier ~1,000 searches/month, then $0.002 per search
- **Combined**: Very affordable for most applications

### Response Times
- Regular chat: 1-3 seconds
- With web search: 3-5 seconds
- With document generation: 5-8 seconds
- Streaming starts: Immediate


[Your License Here]

## 👥 Support

For questions, issues, or contributions:
- **Issues**: Open a GitHub issue
- **Documentation**: Check the docs folder
- **API**: Visit http://localhost:8000/docs when running

## 🌟 Acknowledgments

- OpenRouter for AI model access
- Tavily for web search capabilities
- FastAPI community
- Open source contributors

---

**Built with ❤️ for better healthcare accessibility**

**Version**: 2.0  
**Last Updated**: October 2025  
**Status**: Production Ready ✅

