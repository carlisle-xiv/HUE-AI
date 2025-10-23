# Multi Disease Detector

An AI-powered conversational health consultant that provides patients with intelligent health guidance and symptom analysis.

## Overview

The Multi Disease Detector is a sophisticated feature that allows patients to have natural conversations with an AI health consultant powered by OpenAI's **gpt-oss-120b** model (117B parameters) via HuggingFace Inference API. The system maintains session context across conversations and uses patient medical data to provide personalized health insights.

## Features

- **Conversational AI**: Natural language interactions with openai/gpt-oss-120b (117B parameters)
- **HuggingFace Inference API**: No local GPU/RAM required, instant startup
- **Configurable Reasoning**: Adjust reasoning effort (low, medium, high)
- **Session Management**: Multiple concurrent sessions per patient with unique session IDs
- **Context-Aware**: Integrates optional patient data (vitals, conditions, habits, consultations)
- **Risk Assessment**: Automatic evaluation of health risks with medical disclaimers
- **Persistent History**: Complete conversation history stored and retrievable

## Architecture

### Database Models

#### ChatSession
- Tracks individual conversation sessions
- Links to patient
- Stores session metadata (title, status, timestamps)
- Supports multiple concurrent sessions per patient

#### ChatMessage
- Individual messages within a session
- Stores role (USER/ASSISTANT/SYSTEM), content, and metadata
- Maintains chronological order via timestamps

### API Endpoints

All endpoints are prefixed with `/api/v1/multi-disease-detector`

#### POST `/chat`
Main chat endpoint for conversational interactions.

**Request Body:**
```json
{
  "message": "I've been experiencing headaches lately",
  "session_id": "optional-uuid-for-ongoing-conversation",
  "patient_id": "required-for-new-sessions",
  "vitals_data": {
    "blood_pressure_systolic": 130,
    "blood_pressure_diastolic": 85
  },
  "conditions_data": {
    "conditions": [
      {
        "condition_name": "Hypertension",
        "status": "ACTIVE",
        "severity": "MILD"
      }
    ]
  }
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "message": "AI-generated health advice...",
  "risk_assessment": "MEDIUM",
  "should_see_doctor": true,
  "disclaimer": "Medical disclaimer text..."
}
```

#### GET `/sessions/{patient_id}`
List all chat sessions for a patient with pagination and filtering.

**Query Parameters:**
- `skip`: Number of sessions to skip (default: 0)
- `limit`: Maximum sessions to return (default: 20)
- `status_filter`: Filter by status (ACTIVE, CLOSED, ARCHIVED)

#### GET `/sessions/{session_id}/history`
Retrieve complete conversation history for a session.

#### POST `/sessions/{session_id}/close`
Mark a session as closed (status = CLOSED).

#### DELETE `/sessions/{session_id}`
Delete a session and all its messages (irreversible).

## Optional Context Data

The chat endpoint accepts optional patient context data to provide more personalized responses:

### ConsultationData
- chief_complaint
- history_of_present_illness
- assessment
- diagnosis_codes
- treatment_plan
- doctor_notes

### VitalsData
- blood_type
- blood_pressure (systolic/diastolic)
- heart_rate_bpm
- temperature_celsius
- respiratory_rate
- oxygen_saturation
- glucose_level
- weight_kg, height_cm, bmi

### HabitsData
Array of habit entries:
- habit_type (e.g., SLEEP, WATER_INTAKE, EXERCISE)
- target_value, target_unit
- actual_value
- notes

### ConditionsData
Array of medical conditions:
- condition_name
- status (ACTIVE, RESOLVED, CHRONIC, REMISSION)
- severity (MILD, MODERATE, SEVERE, CRITICAL)
- diagnosed_date
- notes

### AIConsultationData
- symptoms_described
- ai_suggested_conditions
- ai_recommendations
- risk_assessment

## HuggingFace Inference API

The feature uses HuggingFace's Inference API to access the `openai/gpt-oss-120b` model:

1. No model loading required - instant startup
2. API calls to HuggingFace infrastructure
3. No local GPU/VRAM requirements
4. Harmony response format automatically applied
5. Configurable reasoning levels

### Configuration

Key configuration constants in `service.py`:

```python
MODEL_NAME = "openai/gpt-oss-120b"  # HuggingFace model
REASONING_LEVEL = "medium"          # Options: low, medium, high
MAX_HISTORY_MESSAGES = 10           # Context window limit
MAX_RESPONSE_TOKENS = 1024          # Maximum response length
HUGGINGFACE_API_KEY = os.getenv()   # From environment variables
```

### Setup Requirements

1. **HuggingFace API Key**: Get from [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. **Environment Variable**: Add `HUGGINGFACE_API_KEY` to your `.env` file
3. **Dependencies**: `huggingface-hub[inference]` (already in requirements.txt)

See `HUGGINGFACE_SETUP.md` for detailed setup instructions.

## Risk Assessment

The system automatically evaluates health risk based on keywords and context:

- **EMERGENCY**: Immediate medical attention required
- **HIGH**: Should see a doctor soon
- **MEDIUM**: Monitor symptoms, consider consultation
- **LOW**: General health information

Keywords are categorized by severity to trigger appropriate risk levels.

## Usage Example

### Starting a New Conversation

```bash
curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have been feeling dizzy lately",
    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
    "vitals_data": {
      "blood_pressure_systolic": 140,
      "blood_pressure_diastolic": 90
    }
  }'
```

### Continuing a Conversation

```bash
curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "The dizziness happens mostly in the morning",
    "session_id": "returned-session-uuid"
  }'
```

## Database Migration

Run the migration to create the required tables:

```bash
cd /path/to/HUE-AI
source locale/bin/activate
alembic upgrade head
```

This creates:
- `chat_sessions` table
- `chat_messages` table

## Dependencies

Required Python packages (already in requirements.txt):
- `huggingface-hub[inference]==0.26.2` - HuggingFace Inference API client
- `python-dotenv==1.0.1` - Environment variable management

## Logging

The feature includes comprehensive logging:
- Model loading status
- Session creation/updates
- Chat exchanges
- Error conditions

Logs use Python's `logging` module with INFO level by default.

## Security Considerations

1. **Patient Data Privacy**: All patient data is optional and provided by the client
2. **Session Validation**: Sessions are validated against patient ownership
3. **Medical Disclaimer**: Every response includes a disclaimer
4. **Error Handling**: Graceful degradation if model is unavailable

## Future Enhancements

Potential improvements:
- Fine-tune gpt-oss-120b on medical literature
- Implement more sophisticated risk assessment ML model
- Add multi-language support
- Integrate with EHR systems for automatic context loading
- Voice input/output support
- Real-time streaming responses
- Switch to dedicated HuggingFace endpoint for high-volume usage
- Implement function calling for lab results lookup

## Support

For issues or questions about the Multi Disease Detector feature, please refer to the main HUE-AI documentation or contact the development team.

