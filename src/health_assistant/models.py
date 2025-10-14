from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Text, Boolean, String, ForeignKey
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class MessageType(str, Enum):
    """Enum for message types"""

    TEXT = "text"
    IMAGE = "image"


class MessageRole(str, Enum):
    """Enum for message roles"""

    USER = "user"
    ASSISTANT = "assistant"


class HealthSession(SQLModel, table=True):
    """
    Model for health assistant conversation sessions.
    Each session represents a unique conversation with context.
    """

    __tablename__ = "health_sessions"

    # Pydantic config to avoid warning with field names starting with 'model_'
    model_config = {"protected_namespaces": ()}

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    user_id: Optional[str] = Field(
        default=None, max_length=100, index=True
    )  # Optional: for user tracking
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=True, index=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = Field(default=None)

    # Session metadata - using Text to match existing database
    session_metadata: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # Relationships
    messages: List["HealthMessage"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self):
        return f"<HealthSession(id={self.id}, active={self.is_active}, created={self.created_at})>"


class HealthMessage(SQLModel, table=True):
    """
    Model for individual messages within a health assistant session.
    Stores both user inputs and AI responses with support for text and images.
    """

    __tablename__ = "health_messages"

    # Pydantic config to avoid warning with field names starting with 'model_'
    model_config = {"protected_namespaces": ()}

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    session_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("health_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # Message content
    role: MessageRole = Field(sa_column_kwargs={"nullable": False})
    message_type: MessageType = Field(default=MessageType.TEXT)
    content: str = Field(
        sa_column=Column(Text, nullable=False)
    )  # Text content or description

    # Image support
    image_path: Optional[str] = Field(
        default=None, max_length=500
    )  # Path to stored image if applicable
    image_url: Optional[str] = Field(
        default=None, max_length=500
    )  # URL to image if applicable

    # AI response metadata
    model_used: Optional[str] = Field(
        default=None, max_length=100
    )  # Which HF model was used
    confidence_score: Optional[str] = Field(
        default=None, max_length=50
    )  # AI confidence if available

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Message metadata - using Text to match existing database
    message_metadata: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # Relationships
    session: Optional[HealthSession] = Relationship(back_populates="messages")

    def __repr__(self):
        return f"<HealthMessage(id={self.id}, session={self.session_id}, role={self.role}, type={self.message_type})>"
