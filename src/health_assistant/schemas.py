from sqlmodel import SQLModel
from typing import Optional, List
from datetime import datetime
from src.health_assistant.models import MessageType, MessageRole


# Session Schemas
class HealthSessionBase(SQLModel):
    """Base schema for health session"""

    user_id: Optional[str] = None
    session_metadata: Optional[str] = None


class HealthSessionCreate(HealthSessionBase):
    """Schema for creating a new health session"""

    pass


class HealthSessionResponse(HealthSessionBase):
    """Schema for health session response"""

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Message Schemas
class HealthMessageBase(SQLModel):
    """Base schema for health message"""

    content: str
    message_type: MessageType = MessageType.TEXT
    image_url: Optional[str] = None
    message_metadata: Optional[str] = None


class HealthMessageCreate(HealthMessageBase):
    """Schema for creating a new message"""

    session_id: str


class HealthMessageResponse(HealthMessageBase):
    """Schema for health message response"""

    id: str
    session_id: str
    role: MessageRole
    image_path: Optional[str] = None
    model_used: Optional[str] = None
    confidence_score: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Conversation Schemas
class ConversationResponse(SQLModel):
    """Schema for full conversation response"""

    session: HealthSessionResponse
    messages: List[HealthMessageResponse]

    model_config = {"from_attributes": True}


# Chat Endpoint Schemas
class ChatRequest(SQLModel):
    """Schema for chat request"""

    prompt: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    image_base64: Optional[str] = None  # Base64 encoded image
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7


class ChatResponse(SQLModel):
    """Schema for chat response"""

    session_id: str
    message_id: str
    response: str
    model_used: str
    timestamp: datetime
    has_image: bool = False
    metadata: Optional[dict] = None

    model_config = {"from_attributes": True}


class SessionListResponse(SQLModel):
    """Schema for listing sessions"""

    sessions: List[HealthSessionResponse]
    total: int
