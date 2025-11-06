"""
Simplified, client-friendly schemas for Multi Disease Detector chat endpoint.
These provide a simple API surface while leveraging OpenAI infrastructure internally.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class SimplifiedChatRequest(BaseModel):
    """
    Simplified chat request for client applications.
    
    This provides a user-friendly API without exposing complex internals.
    All model configuration (temperature, max_tokens, etc.) is handled automatically.
    """
    message: str = Field(..., description="User's message/question (REQUIRED)")
    patient_id: Optional[UUID] = Field(None, description="Patient UUID for tracking and session management")
    stream: bool = Field(False, description="Enable streaming responses (SSE)")
    
    # Optional image as base64 string
    image: Optional[str] = Field(
        None,
        description="Optional base64-encoded image (without data URI prefix). Just the base64 string."
    )
    
    # Optional patient context data (all fields optional)
    consultation_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Recent consultation information"
    )
    vitals_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Latest vital signs"
    )
    habits_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Patient habits tracking"
    )
    conditions_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Active medical conditions"
    )
    ai_consultation_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Previous AI consultation data"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "What are the symptoms of type 2 diabetes?",
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "stream": False,
                "vitals_data": {
                    "blood_pressure_systolic": 130,
                    "blood_pressure_diastolic": 85,
                    "heart_rate_bpm": 75
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
        }
    )


class SimplifiedChatResponse(BaseModel):
    """
    Simplified chat response.
    
    Returns AI-generated response with medical metadata in a clean format.
    """
    session_id: UUID = Field(..., description="Session ID for conversation continuity")
    message: str = Field(..., description="AI-generated response")
    risk_assessment: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, EMERGENCY")
    should_see_doctor: bool = Field(..., description="Whether patient should consult a doctor")
    tools_used: List[str] = Field(default_factory=list, description="Tools used during generation (e.g., web search)")
    disclaimer: str = Field(..., description="Medical disclaimer")
    thinking_summary: Optional[str] = Field(None, description="Summary of AI's reasoning process")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "660e8400-e29b-41d4-a716-446655440000",
                "message": "Type 2 diabetes symptoms include increased thirst, frequent urination, unexplained weight loss...",
                "risk_assessment": "MEDIUM",
                "should_see_doctor": True,
                "tools_used": ["tavily_web_search"],
                "disclaimer": "⚠️ Important Disclaimer: This is an AI assistant and not a replacement for professional medical advice...",
                "thinking_summary": "Analyzed symptoms → Searched latest guidelines → Generated explanation"
            }
        }
    )


class SimplifiedStreamEvent(BaseModel):
    """
    Simplified streaming event for SSE responses.
    
    Different event types:
    - content: Text content chunks
    - thinking: AI reasoning process
    - tool: Tool usage information
    - complete: Final event with metadata
    - error: Error occurred
    """
    type: str = Field(..., description="Event type: content, thinking, tool, complete, error")
    data: Any = Field(..., description="Event data (varies by type)")
    timestamp: Optional[str] = Field(None, description="Event timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "content",
                    "data": "Type 2 diabetes",
                    "timestamp": "2025-11-03T10:00:00"
                },
                {
                    "type": "thinking",
                    "data": "Searching for latest treatment guidelines...",
                    "timestamp": "2025-11-03T10:00:01"
                },
                {
                    "type": "tool",
                    "data": {
                        "tool_name": "tavily_web_search",
                        "status": "executing"
                    },
                    "timestamp": "2025-11-03T10:00:02"
                },
                {
                    "type": "complete",
                    "data": {
                        "session_id": "uuid",
                        "risk_assessment": "MEDIUM",
                        "should_see_doctor": True,
                        "tools_used": ["tavily_web_search"]
                    },
                    "timestamp": "2025-11-03T10:00:10"
                }
            ]
        }
    )

