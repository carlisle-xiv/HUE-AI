"""
FastAPI router for Multi Disease Detector endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func

from src.database import get_db
from .models import ChatSession, ChatMessage
from .schemas import (
    ChatRequest,
    ChatResponse,
    SessionResponse,
    SessionListResponse,
    SessionHistoryResponse,
    MessageHistory
)
from .service import process_chat_request

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/multi-disease-detector",
    tags=["Multi Disease Detector"],
    responses={404: {"description": "Not found"}}
)


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_ai(
    request: ChatRequest,
    session_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> ChatResponse:
    """
    Main chat endpoint for conversational AI health consultant.
    
    **Query Parameters:**
    - **session-id** (optional): Session UUID for ongoing conversations. Omit for new sessions.
    
    **Request Body (only 'message' is required, all else optional):**
    - **message**: User's message/prompt (REQUIRED)
    - **patient_id**: Patient UUID for tracking
    - **consultation_data**: Recent consultation information (ALL fields optional)
    - **vitals_data**: Latest vital signs (ALL fields optional)
    - **habits_data**: Patient habits tracking (ALL fields optional)
    - **conditions_data**: Active medical conditions (ALL fields optional)
    - **ai_consultation_data**: Previous AI consultation data (ALL fields optional)
    
    **Returns:** AI-generated response with risk assessment and medical disclaimer.
    """
    try:
        # Inject session_id from query parameter into request
        request.session_id = session_id
        response = await process_chat_request(db=db, request=request)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )


@router.get("/sessions/{patient_id}", response_model=SessionListResponse)
async def get_patient_sessions(
    patient_id: UUID,
    skip: int = 0,
    limit: int = 20,
    status_filter: str = None,
    db: Session = Depends(get_db)
) -> SessionListResponse:
    """
    Get all chat sessions for a patient.
    
    - **patient_id**: Patient's UUID
    - **skip**: Number of sessions to skip (pagination)
    - **limit**: Maximum number of sessions to return
    - **status_filter**: Optional filter by status (ACTIVE, CLOSED, ARCHIVED)
    """
    try:
        # Build query
        statement = select(ChatSession).where(ChatSession.patient_id == patient_id)
        
        if status_filter:
            statement = statement.where(ChatSession.status == status_filter)
        
        # Get total count
        count_statement = select(func.count()).select_from(
            statement.subquery()
        )
        total = db.exec(count_statement).one()
        
        # Get sessions with pagination
        statement = statement.order_by(ChatSession.last_message_at.desc()).offset(skip).limit(limit)
        sessions = db.exec(statement).all()
        
        # Build response with message counts
        session_responses = []
        for session in sessions:
            # Count messages in session
            msg_count_stmt = select(func.count()).where(ChatMessage.session_id == session.id)
            msg_count = db.exec(msg_count_stmt).one()
            
            session_responses.append(
                SessionResponse(
                    id=session.id,
                    patient_id=session.patient_id,
                    title=session.title,
                    status=session.status,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    last_message_at=session.last_message_at,
                    message_count=msg_count
                )
            )
        
        return SessionListResponse(
            sessions=session_responses,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error getting patient sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving sessions"
        )


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: UUID,
    db: Session = Depends(get_db)
) -> SessionHistoryResponse:
    """
    Get complete conversation history for a session.
    
    - **session_id**: Session UUID
    
    Returns the session details and all messages in chronological order.
    """
    try:
        # Get session
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # Get all messages
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = db.exec(statement).all()
        
        # Build response
        message_history = [
            MessageHistory(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                metadata=msg.message_metadata,
                created_at=msg.created_at
            )
            for msg in messages
        ]
        
        return SessionHistoryResponse(
            session_id=session.id,
            title=session.title,
            status=session.status,
            created_at=session.created_at,
            last_message_at=session.last_message_at,
            messages=message_history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving session history"
        )


@router.post("/sessions/{session_id}/close", status_code=status.HTTP_200_OK)
async def close_session(
    session_id: UUID,
    db: Session = Depends(get_db)
) -> dict:
    """
    Close an active chat session.
    
    - **session_id**: Session UUID to close
    
    Changes the session status to CLOSED.
    """
    try:
        # Get session
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # Update status
        session.status = "CLOSED"
        session.updated_at = datetime.utcnow()
        db.add(session)
        db.commit()
        
        return {
            "message": "Session closed successfully",
            "session_id": str(session_id),
            "status": "CLOSED"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while closing the session"
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete a chat session and all its messages.
    
    - **session_id**: Session UUID to delete
    
    **Warning**: This action is irreversible.
    """
    try:
        # Get session
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # Delete session (cascade will delete messages)
        db.delete(session)
        db.commit()
        
        return {
            "message": "Session deleted successfully",
            "session_id": str(session_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the session"
        )


# Import datetime for close_session
from datetime import datetime

