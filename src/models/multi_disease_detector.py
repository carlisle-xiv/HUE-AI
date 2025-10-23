"""
Multi Disease Detector models for AI-powered conversational health consultant.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB


class ChatSession(SQLModel, table=True):
    """Chat session for multi-disease detector conversations"""
    
    __tablename__ = "chat_sessions"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    title: Optional[str] = Field(default=None, max_length=500)  # Auto-generated from first message
    status: str = Field(default="ACTIVE", max_length=20, index=True)  # ACTIVE, CLOSED, ARCHIVED
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = Field(default=None, index=True)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="chat_sessions")
    messages: list["ChatMessage"] = Relationship(back_populates="session", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ChatMessage(SQLModel, table=True):
    """Individual chat messages in a session"""
    
    __tablename__ = "chat_messages"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    session_id: UUID = Field(foreign_key="chat_sessions.id", index=True)
    role: str = Field(max_length=20, index=True)  # USER, ASSISTANT, SYSTEM
    content: str = Field(sa_column=Column(Text))
    message_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSONB))  # For risk_assessment, disclaimer, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    session: ChatSession = Relationship(back_populates="messages")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import Patient

