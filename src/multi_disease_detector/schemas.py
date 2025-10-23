"""
Pydantic schemas for Multi Disease Detector API.
Flattened schema structure to avoid circular reference issues.
"""

from datetime import datetime, date
from typing import Optional, List, Any, Dict
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# ===== FLATTENED INPUT SCHEMAS - Using Dict instead of nested models =====

class ChatRequest(BaseModel):
    """
    Main chat request with optional patient context data.
    Only 'message' is required - all other fields are optional.
    Note: session_id comes from query parameter, not request body.
    """
    message: str = Field(..., description="User's message/prompt (REQUIRED)")
    patient_id: Optional[UUID] = Field(None, description="Patient ID for tracking")
    session_id: Optional[UUID] = None  # Set from query parameter, not sent in body
    
    # Optional context data - using Dict for maximum flexibility
    consultation_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Recent consultation information (all fields optional)"
    )
    vitals_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Latest vital signs (all fields optional)"
    )
    habits_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Patient habits tracking - expects {habits: [list of habit dicts]}"
    )
    conditions_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Active medical conditions - expects {conditions: [list of condition dicts]}"
    )
    ai_consultation_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Previous AI consultation data (all fields optional)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "I've been experiencing frequent headaches lately, what could be the cause?",
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "consultation_data": {
                    "chief_complaint": "Persistent headaches for 2 weeks",
                    "history_of_present_illness": "Patient reports daily headaches, worse in morning",
                    "assessment": "Possible tension headaches",
                    "treatment_plan": "Prescribed pain management and stress reduction"
                },
                "vitals_data": {
                    "blood_type": "O+",
                    "blood_pressure_systolic": 130,
                    "blood_pressure_diastolic": 85,
                    "heart_rate_bpm": 75,
                    "temperature_celsius": 37.2,
                    "oxygen_saturation": 98.5
                },
                "habits_data": {
                    "habits": [
                        {
                            "habit_type": "SLEEP",
                            "target_value": 8.0,
                            "target_unit": "hours",
                            "actual_value": 5.5,
                            "date": "2025-10-23"
                        },
                        {
                            "habit_type": "WATER_INTAKE",
                            "target_value": 2.0,
                            "target_unit": "liters",
                            "actual_value": 1.8
                        }
                    ]
                },
                "conditions_data": {
                    "conditions": [
                        {
                            "condition_name": "Hypertension",
                            "diagnosed_date": "2022-06-20",
                            "status": "ACTIVE",
                            "severity": "MILD",
                            "notes": "Well-controlled with medication"
                        }
                    ]
                },
                "ai_consultation_data": {
                    "symptoms_described": "Previous headache consultation",
                    "risk_assessment": "MEDIUM",
                    "should_see_doctor": True
                }
            }
        }
    )


# ===== RESPONSE SCHEMAS =====
class ChatResponse(BaseModel):
    """Response from the AI health consultant"""
    session_id: UUID = Field(..., description="Session ID for this conversation")
    message: str = Field(..., description="AI-generated response")
    risk_assessment: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, EMERGENCY")
    should_see_doctor: bool = Field(..., description="Whether the patient should consult a doctor")
    disclaimer: str = Field(..., description="Medical disclaimer")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "660e8400-e29b-41d4-a716-446655440000",
                "message": "Based on your symptoms and medical history, frequent headaches combined with elevated blood pressure and poor sleep could be related...",
                "risk_assessment": "MEDIUM",
                "should_see_doctor": True,
                "disclaimer": "⚠️ **Important Disclaimer**: This is an AI assistant and not a replacement for professional medical advice..."
            }
        }
    )


class MessageHistory(BaseModel):
    """Individual message in conversation history"""
    id: UUID
    role: str = Field(..., description="USER, ASSISTANT, or SYSTEM")
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionHistoryResponse(BaseModel):
    """Complete session history with messages"""
    session_id: UUID
    title: Optional[str]
    status: str
    created_at: datetime
    last_message_at: Optional[datetime]
    messages: List[MessageHistory]

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    """Session information without messages"""
    id: UUID
    patient_id: UUID
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    """List of sessions for a patient"""
    sessions: List[SessionResponse]
    total: int
