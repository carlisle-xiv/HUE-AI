# HUE-AI

AI-powered health and wellness platform built with FastAPI, integrating cutting-edge AI models for comprehensive medical assistance, diagnostics, and healthcare management.

**🎯 What Sets HUE-AI Apart:**
- 🧠 **Multiple AI-Powered Features**: Not just chat - includes drug suggestions with safety checks and authenticity verification
- 🇬🇭 **Ghana-Specific**: Integrated Ghana STG and EML for localized healthcare
- 🔒 **Safety-First**: Multi-level drug interaction checking, allergy validation, and risk assessment
- 🌐 **Current Information**: Real-time web search for latest medical guidelines
- 💼 **Production-Ready**: Complete healthcare management platform, not just a demo
- ⚡ **Instant Startup**: No model downloads, API-based for immediate deployment

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
- ✅ **No Local GPU Required** - All processing via OpenRouter API (instant startup)

### 2. Drug Suggester 💊

**Intelligent medication recommendation system for healthcare providers in Ghana.**

#### Core Capabilities:
- **Comprehensive Patient Analysis**: Reviews medical history, allergies, and current medications
- **Safety Checks**: Drug-drug interactions via RxNav API, allergy checking, contraindication verification
- **Evidence-Based Guidelines**: Searches Ghana Standard Treatment Guidelines and Essential Medicine List
- **Facility Integration**: Multi-pharmacy inventory checking with stock levels and pricing
- **AI-Powered Recommendations**: Intelligent drug selection with personalized dosing
- **Audit Trail**: Complete logging of all suggestions for clinical review

#### Features:
- 🛡️ **Multi-level Safety**: Interaction detection (safe/minor/moderate/severe)
- 📚 **Ghana Guidelines**: Web-based current Ghana STG and EML integration
- 🏥 **Real-time Inventory**: Checks drug availability across multiple facilities
- 🤖 **Intelligent Dosing**: Age, weight, and condition-specific calculations
- 📝 **Clinical Rationale**: Explains drug selection and dosing decisions

### 3. Drug Authenticity Checker 🔍

**Automated drug verification system to combat counterfeit medications.**

#### Features:
- 🔎 **Web Search Verification**: Automated searches across trusted sources
- 🏭 **Manufacturer Verification**: Validates manufacturer and regulatory approval
- ⚠️ **Counterfeit Alerts**: Detects and reports counterfeit warnings
- 💾 **Result Caching**: 30-day cache for improved performance
- 📊 **Confidence Scoring**: Provides verification confidence levels
- 🔗 **Source References**: Links to verification sources (FDA, drugs.com, etc.)

### 4. Comprehensive Healthcare Platform 🏥

Full-featured healthcare management system with:
- **Patient & Doctor Management**: Complete profiles and specializations
- **Hospital Operations**: Bed management, department tracking
- **Appointment System**: Scheduling and consultation management
- **Prescription Management**: E-prescriptions and medication tracking
- **Pharmacy Integration**: Medicine inventory and dispensing
- **Insurance Integration**: Claims and coverage management
- **Medical Records**: Lab tests, imaging results, and clinical notes
- **Reference Data**: ICD-10 codes, CPT codes, medication database

## 🔄 Feature Comparison

| Feature | Multi-Disease Detector | Drug Suggester | Drug Authenticity | Healthcare Platform |
|---------|----------------------|----------------|-------------------|-------------------|
| **AI Powered** | ✅ gpt-oss-120b | ✅ gpt-oss-120b | ✅ via web search | ❌ Traditional |
| **Target Users** | Doctors(primarily), patients(casual) | Healthcare Providers | Everyone | Healthcare System |
| **Primary Use** | Symptom analysis | Medication recommendations | Drug verification | Data management |
| **Real-time Streaming** | ✅ Yes | ❌ No | ❌ No | N/A |
| **Web Search** | ✅ Tavily | ✅ Tavily | ✅ Tavily | ❌ No |
| **Database Integration** | ✅ Patient data | ✅ Inventory/RxNav | ✅ Cache | ✅ Full EHR |
| **Document Generation** | ✅ PDF/HTML | ❌ No | ❌ No | ❌ No |
| **Session Management** | ✅ Multi-session | ❌ Single request | ❌ Single request | ✅ Full tracking |
| **Safety Checks** | ✅ Risk assessment | ✅ Interactions/Allergies | ⚠️ Authenticity only | ❌ No |
| **Ghana-Specific** | ❌ General | ✅ STG/EML | ❌ General | ❌ General |

### 🎯 Key Capabilities Summary

**Multi-Disease Detector** is best for:
- ✅ Patient self-assessment and education
- ✅ Understanding medical test results
- ✅ Getting latest treatment information
- ✅ Real-time conversational medical guidance

**Drug Suggester** is best for:
- ✅ Healthcare providers prescribing in Ghana
- ✅ Reducing prescription errors
- ✅ Checking drug availability before prescribing
- ✅ Following Ghana STG and EML guidelines

**Drug Authenticity** is best for:
- ✅ Patients verifying medication legitimacy
- ✅ Pharmacists confirming drug authenticity
- ✅ Combating counterfeit medications
- ✅ Quick verification with trusted sources

**Healthcare Platform** is best for:
- ✅ Complete hospital/clinic management
- ✅ Patient records and appointments
- ✅ Prescription and pharmacy integration
- ✅ Insurance and billing management

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
│   │   ├── multi_disease_detector.py # AI chat sessions
│   │   ├── drug_suggester.py        # Drug suggester models
│   │   └── drug_authenticity.py     # Drug authenticity checks
│   ├── multi_disease_detector/      # AI Medical Assistant Feature
│   │   ├── models.py                # Model re-exports
│   │   ├── schemas.py               # Request/response schemas
│   │   ├── service.py               # Core business logic & AI integration
│   │   ├── router.py                # API endpoints
│   │   ├── tools.py                 # Tool definitions (OpenRouter format)
│   │   ├── tool_service.py          # Tool execution (Tavily integration)
│   │   ├── artifacts.py             # Document generation & PDF conversion
│   │   ├── vision_service.py        # Image analysis capabilities
│   │   └── README.md                # Feature documentation
│   ├── drug_suggester/              # Drug Recommendation System
│   │   ├── router.py                # API endpoints
│   │   ├── schemas.py               # Request/response schemas
│   │   ├── service.py               # Core suggestion logic & AI
│   │   ├── rxnav_service.py         # RxNav API integration
│   │   └── README.md                # Feature documentation
│   └── drug_recommendation/         # Drug Authenticity Verification
│       ├── router.py                # API endpoints
│       ├── schemas.py               # Request/response schemas
│       └── service.py               # Authenticity checking logic
├── alembic/                         # Database migrations
│   └── versions/                    # Migration files
├── requirements.txt                 # Python dependencies
├── seed_test_data.py                # General test data seeder
├── seed_drug_suggester_test_data.py # Drug suggester test data
├── test_drug_suggester_comprehensive.py # Drug suggester tests
├── test_risk_assessment.py          # Risk assessment tests
├── test_streaming_fix.py            # Streaming functionality tests
└── test_client_streaming.py         # Client-side streaming tests
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL database
- API Keys:
  - [OpenRouter](https://openrouter.ai/) 
  - [Tavily](https://tavily.com/) 

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

2. **Tavily** (Required for web search):
   - Sign up at [tavily.com](https://tavily.com/)
   - Free tier: ~1,000 searches/month (sufficient for testing)
   - Copy your API key (starts with `tvly-`)
   - Used by: All features for current medical information
   
3. **RxNav API** (Automatic - No key needed):
   - Free NIH public API for drug interactions
   - No registration required
   - Automatically used by Drug Suggester

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
- Drug suggester (allergies, interactions cache, suggestions)
- Drug authenticity checks

**Optional: Seed Test Data**

```bash
# Seed general test data (patients, doctors, hospitals)
python seed_test_data.py

# Seed drug suggester specific data (drug codes, inventory, allergies)
python seed_drug_suggester_test_data.py
```

This is helpful for testing and development.

### 5. Run the Application

```bash
# Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the main.py script
python main.py
```

The API will be available at `http://localhost:8000`

**✅ Fast Startup**: Application starts instantly using OpenRouter's API. No model downloads required!

### 6. Test the System

```bash
# Test drug suggester
python test_drug_suggester_comprehensive.py

# Test risk assessment
python test_risk_assessment.py

# Test streaming functionality
python test_streaming_fix.py

# Test client-side streaming
python test_client_streaming.py
```

This validates:
- ✅ Drug suggester recommendations
- ✅ Risk assessment algorithms
- ✅ Streaming functionality
- ✅ Tool execution
- ✅ RxNav integration
- ✅ Tavily web search

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs` (Interactive API testing)
- **ReDoc**: `http://localhost:8000/redoc` (Detailed documentation)

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
| `/sessions/{patient_id}` | GET | List all chat sessions for a patient |
| `/sessions/{session_id}/history` | GET | Get conversation history |
| `/sessions/{session_id}/close` | POST | Close a session |

#### Drug Suggester

**Base URL:** `/api/v1/drug-suggester`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/suggest` | POST | Generate drug suggestions for patient |
| `/health` | GET | Service health check |
| `/` | GET | Service information |

#### Drug Authenticity

**Base URL:** `/api/v1/drug-authenticity`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/check` | POST | Verify drug authenticity |
| `/health` | GET | Service health check |
| `/` | GET | Service information |

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

#### 4. Drug Suggestions

```bash
curl -X POST "http://localhost:8000/api/v1/drug-suggester/suggest" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
    "diagnosis": "Type 2 Diabetes Mellitus",
    "additional_conditions": ["Hypertension"],
    "doctor_id": "660e8400-e29b-41d4-a716-446655440001",
    "facility_ids": ["770e8400-e29b-41d4-a716-446655440002"]
  }'
```

**Response includes:**
- Primary suggestions (in-stock medications)
- Alternate suggestions (out-of-stock alternatives)
- Allergy alerts and interaction warnings
- Ghana STG/EML guideline notes
- Facility inventory details with pricing
- Clinical rationale for each recommendation

#### 5. Drug Authenticity Check

```bash
curl -X POST "http://localhost:8000/api/v1/drug-authenticity/check" \
  -H "Content-Type: application/json" \
  -d '{
    "drug_name": "Paracetamol"
  }'
```

**Response includes:**
- Authentication status (authentic/counterfeit/unknown)
- Confidence score (0.0 - 1.0)
- Manufacturer information
- FDA/regulatory approval status
- Warning alerts
- Verification sources with URLs

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

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         HUE-AI Platform                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┬────────────────┐
            ▼               ▼               ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌────────────┐
    │Multi-Disease │ │Drug Suggester│ │   Drug   │ │Healthcare  │
    │   Detector   │ │              │ │Authenticity│ │ Platform   │
    └──────┬───────┘ └──────┬───────┘ └────┬─────┘ └─────┬──────┘
           │                │               │             │
           ▼                ▼               ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐
    │  OpenRouter  │ │  RxNav API   │ │  Tavily  │ │PostgreSQL│
    │(Model)│        │(Interactions)│ │(Search)  │ │   DB     │
    └──────────────┘ └──────────────┘ └──────────┘ └──────────┘
```

#### Multi-Disease Detector Flow

```
User Request → API Endpoint → Service Layer → AI Model (OpenRouter)
                                   ↓
                          Tool Execution (if needed)
                    ├── Tavily Web Search
                    ├── Lab Explanation Generator
                    ├── Imaging Analysis Generator
                    └── Medical Summary Generator
                                   ↓
                         AI Synthesis + Artifacts
                                   ↓
                          Response to User
```

#### Drug Suggester Flow

```
Request → Patient Context → Ghana Guidelines (Tavily)
              ↓                      ↓
         RxNav Check → AI Selection (OpenRouter)
              ↓                      ↓
       Inventory Match → Safety Validation
              ↓                      ↓
         Response with Recommendations
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
   - Add test cases to test files
   - Test via API endpoints using `/docs` interactive UI
   - Verify streaming functionality with `test_streaming_fix.py`

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
python test_drug_suggester_comprehensive.py
python test_risk_assessment.py
python test_streaming_fix.py
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

### RxNav Integration Issues

**Issue**: Drug interaction checking not working
```bash
# Test RxNav API directly
curl "https://rxnav.nlm.nih.gov/REST/interaction/list.json?rxcuis=207106+152923"

# Check service logs for RxNav errors
# Falls back gracefully to contraindication checking only
```

### Drug Suggester Issues

**Issue**: No drug suggestions returned
- Verify patient has required data (conditions, vitals)
- Check facility inventory has drugs in stock
- Review Ghana guidelines search results in logs
- Ensure OpenRouter API key is valid
- Check database for drug_codes table population

**Issue**: Cache not working for RxNav
- Verify `drug_interaction_cache` table exists
- Check cache expiry (default: 7 days)
- Review logs for cache hit/miss rates

## 🛠️ Technologies Used

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations
- **PostgreSQL** - Relational database
- **Pydantic** - Data validation

### AI & ML
- **OpenRouter** - AI model API gateway
- **OpenAI gpt-oss-120b** - 117B parameter model for medical conversations
- **Tavily** - Web search API for current medical information
- **RxNav API** - NIH drug interaction database
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
- **RxNav API**: https://rxnav.nlm.nih.gov/
- **FastAPI**: https://fastapi.tiangolo.com/

## 🎯 Use Cases

### For Patients
- 📱 Quick symptom assessment with AI
- 📊 Understanding lab results and test values
- 🏥 Interpreting imaging reports (X-ray, CT, MRI)
- 💊 Medication information and safety
- 🔍 Access to current treatment guidelines
- 🔎 Drug authenticity verification

### For Healthcare Providers
- 📄 Generate patient-friendly medical explanations
- 💊 AI-powered drug suggestions with safety checks
- 🔎 Quick reference to Ghana STG and EML
- 📋 Pre-consultation patient insights
- 📊 Visual reports for patient education
- 🛡️ Automated interaction checking
- 🏥 Multi-facility inventory management

### For Pharmacists
- 💊 Drug interaction checking via RxNav
- 🏭 Drug authenticity verification
- 📦 Inventory management across facilities
- 💰 Pricing and stock level tracking
- 📋 Prescription validation

### For Researchers
- 🧬 Medical data management
- 📈 Patient cohort tracking
- 🔬 Clinical trial coordination
- 📊 Drug suggestion audit trails

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
- Add docstrings to functions and classes
- Update main README and feature-specific READMEs
- Add comprehensive tests for new functionality
- Keep PRs focused and atomic
- Use type hints for better code clarity
- Log important operations and errors

### Feature-Specific Documentation
Each major feature has its own README:
- `src/multi_disease_detector/README.md` - AI medical assistant details
- `src/drug_suggester/README.md` - Drug suggestion system details

When modifying features, update both the main README and feature README.

## 📊 Performance & Costs

### API Usage Costs
- **OpenRouter** (gpt-oss-120b): Pay-per-use (~$0.001-0.01 per request)
- **Tavily** (Web Search): Free tier ~1,000 searches/month, then $0.002 per search
- **RxNav API** (Drug Interactions): Free (NIH public API)
- **Combined**: Very affordable for production applications

### Response Times

**Multi-Disease Detector:**
- Regular chat: 1-3 seconds
- With web search: 3-5 seconds
- With document generation: 5-8 seconds
- Streaming: Immediate start

**Drug Suggester:**
- Average: 3-5 seconds
- Components:
  - Patient context: ~0.5s
  - Tavily searches: ~1-2s
  - RxNav checks: ~0.5s (cached) or ~2s (uncached)
  - AI generation: ~2-3s
  - Safety checks: ~0.5s

**Drug Authenticity:**
- Cached results: <100ms
- New searches: 2-4 seconds
- Cache duration: 30 days


[Your License Here]

## 👥 Support

For questions, issues, or contributions:
- **Issues**: Open a GitHub issue
- **Documentation**: Check the docs folder
- **API**: Visit http://localhost:8000/docs when running

## 🌟 Acknowledgments

- **OpenRouter** for AI model access (gpt-oss-120b)
- **Tavily** for real-time web search capabilities
- **NIH RxNav** for comprehensive drug interaction database
- **FastAPI** community for excellent framework and documentation
- **Ghana Health Service** for STG and EML guidelines
- Open source contributors worldwide

---

**Built with ❤️ for better healthcare accessibility**

**Version**: 2.1  
**Last Updated**: November 2025  
**Status**: Staging Ready ✅

