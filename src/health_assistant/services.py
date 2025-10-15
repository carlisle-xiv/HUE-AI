"""
Service layer for Health Assistant
Handles business logic for sessions, messages, and AI interactions
"""

from sqlmodel import Session, select
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import json
import logging

from src.health_assistant.models import (
    HealthSession,
    HealthMessage,
    MessageRole,
    MessageType,
)
from src.health_assistant.model_service import model_service
from PIL import Image

logger = logging.getLogger(__name__)


class HealthAssistantService:
    """Service for managing health assistant conversations"""

    @staticmethod
    def get_or_create_session(
        db: Session,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> HealthSession:
        """
        Get existing session or create a new one.

        Args:
            db: Database session
            session_id: Optional existing session ID
            user_id: Optional user ID for tracking

        Returns:
            HealthSession object
        """
        if session_id:
            # Try to retrieve existing session
            session = db.get(HealthSession, session_id)
            if session:
                # Update last activity
                session.updated_at = datetime.utcnow()
                db.add(session)
                db.commit()
                db.refresh(session)
                return session
            else:
                logger.warning(f"Session {session_id} not found, creating new session")

        # Create new session
        new_session = HealthSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        logger.info(f"Created new session: {new_session.id}")
        return new_session

    @staticmethod
    def get_conversation_history(
        db: Session,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for context.

        Args:
            db: Database session
            session_id: Session ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries with role and content
        """
        statement = (
            select(HealthMessage)
            .where(HealthMessage.session_id == session_id)
            .order_by(HealthMessage.created_at.desc())
            .limit(limit)
        )
        messages = db.exec(statement).all()

        # Reverse to get chronological order and format
        history = []
        for msg in reversed(messages):
            history.append(
                {
                    "role": msg.role.value,
                    "content": msg.content,
                }
            )

        return history

    @staticmethod
    def save_message(
        db: Session,
        session_id: str,
        role: MessageRole,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        model_used: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> HealthMessage:
        """
        Save a message to the database.

        Args:
            db: Database session
            session_id: Session ID
            role: Message role (user or assistant)
            content: Message content
            message_type: Type of message (text or image)
            image_path: Optional image path
            image_url: Optional image URL
            model_used: Model that generated the response
            metadata: Additional metadata

        Returns:
            HealthMessage object
        """
        message = HealthMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            message_type=message_type,
            content=content,
            image_path=image_path,
            image_url=image_url,
            model_used=model_used,
            message_metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    async def process_chat_message(
        db: Session,
        prompt: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        image: Optional[Image.Image] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> Dict:
        """
        Process a chat message and generate AI response.

        Args:
            db: Database session
            prompt: User's prompt/query
            session_id: Optional session ID
            user_id: Optional user ID
            image: Optional PIL Image for analysis
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dictionary with response data
        """
        try:
            # Get or create session
            session = HealthAssistantService.get_or_create_session(
                db, session_id, user_id
            )

            # Get conversation history
            conversation_history = HealthAssistantService.get_conversation_history(
                db, session.id
            )

            # Determine message type
            message_type = MessageType.IMAGE if image else MessageType.TEXT

            # Save user message
            user_message = HealthAssistantService.save_message(
                db=db,
                session_id=session.id,
                role=MessageRole.USER,
                content=prompt,
                message_type=message_type,
            )

            # Generate AI response
            if image:
                # Use LLaVA for image analysis
                response_text, metadata = model_service.generate_image_response(
                    query=prompt,
                    image=image,
                    conversation_history=conversation_history,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                )
                model_used = "llava-1.5-7b-hf"
            else:
                # Use BioMistral for text-only
                response_text, metadata = model_service.generate_text_response(
                    query=prompt,
                    conversation_history=conversation_history,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                )
                model_used = "mistral-7b-instruct"
            # Save AI response
            ai_message = HealthAssistantService.save_message(
                db=db,
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content=response_text,
                message_type=MessageType.TEXT,
                model_used=model_used,
                metadata=metadata,
            )

            # Update session
            session.updated_at = datetime.utcnow()
            db.add(session)
            db.commit()

            return {
                "session_id": session.id,
                "message_id": ai_message.id,
                "response": response_text,
                "model_used": model_used,
                "timestamp": ai_message.created_at,
                "has_image": image is not None,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            raise

    @staticmethod
    def get_session_with_messages(
        db: Session,
        session_id: str,
    ) -> Optional[Dict]:
        """
        Get session with all messages.

        Args:
            db: Database session
            session_id: Session ID

        Returns:
            Dictionary with session and messages or None
        """
        session = db.get(HealthSession, session_id)
        if not session:
            return None

        statement = (
            select(HealthMessage)
            .where(HealthMessage.session_id == session_id)
            .order_by(HealthMessage.created_at.asc())
        )
        messages = db.exec(statement).all()

        return {
            "session": session,
            "messages": messages,
        }

    @staticmethod
    def get_user_sessions(
        db: Session,
        user_id: str,
        active_only: bool = True,
    ) -> List[HealthSession]:
        """
        Get all sessions for a user.

        Args:
            db: Database session
            user_id: User ID
            active_only: Only return active sessions

        Returns:
            List of HealthSession objects
        """
        statement = select(HealthSession).where(HealthSession.user_id == user_id)

        if active_only:
            statement = statement.where(HealthSession.is_active == True)

        statement = statement.order_by(HealthSession.updated_at.desc())
        sessions = db.exec(statement).all()
        return sessions

    @staticmethod
    def end_session(
        db: Session,
        session_id: str,
    ) -> Optional[HealthSession]:
        """
        End/close a session.

        Args:
            db: Database session
            session_id: Session ID

        Returns:
            Updated HealthSession or None
        """
        session = db.get(HealthSession, session_id)
        if session:
            session.is_active = False
            session.ended_at = datetime.utcnow()
            session.updated_at = datetime.utcnow()
            db.add(session)
            db.commit()
            db.refresh(session)
        return session
