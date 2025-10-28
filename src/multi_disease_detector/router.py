"""
FastAPI router for Multi Disease Detector endpoints.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func

from src.database import get_db
from .models import ChatSession, ChatMessage
from .schemas import (
    ChatRequest,
    ChatResponse,
    ChatResponseWithArtifacts,
    SessionResponse,
    SessionListResponse,
    SessionHistoryResponse,
    MessageHistory
)
from .service import (
    process_chat_request,
    process_chat_request_with_tools,
    generate_response_with_tools,
    get_or_create_session,
    build_context_from_data,
    get_session_history,
    build_chat_messages
)

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
async def get_session_history_endpoint(
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


# ===== NEW ENDPOINTS WITH TOOL CALLING AND STREAMING =====

@router.post("/chat/with-tools", response_model=ChatResponseWithArtifacts, status_code=status.HTTP_200_OK)
async def chat_with_tools(
    request: ChatRequest,
    session_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> ChatResponseWithArtifacts:
    """
    Enhanced chat endpoint with tool calling support (web search, document generation).
    
    This endpoint enables the AI to:
    - Search the web for current medical information (Tavily)
    - Generate detailed lab result explanations
    - Generate imaging analysis documents
    - Generate medical summaries
    
    **Query Parameters:**
    - **session-id** (optional): Session UUID for ongoing conversations
    
    **Request Body:**
    - **message**: User's message/prompt (REQUIRED)
    - **patient_id**: Patient UUID for tracking
    - All context data fields are optional (same as /chat endpoint)
    
    **Returns:** 
    - AI-generated response with risk assessment
    - List of tools used
    - Thinking process summary
    - References to any generated artifacts
    """
    try:
        request.session_id = session_id
        response = await process_chat_request_with_tools(db=db, request=request)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in chat/with-tools endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Streaming chat endpoint that shows AI's thinking process in real-time.
    
    Returns Server-Sent Events (SSE) with different event types:
    - **thinking**: AI's reasoning process
    - **tool_call**: When AI decides to use a tool
    - **tool_result**: Results from tool execution
    - **content**: AI's response content (streamed token by token)
    - **done**: Final completion event
    - **error**: Error occurred
    
    **Query Parameters:**
    - **session-id** (optional): Session UUID for ongoing conversations
    
    **Request Body:** Same as /chat endpoint
    
    **Usage Example (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/api/v1/multi-disease-detector/chat/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.type, data.data);
    };
    ```
    """
    try:
        # Get or create session
        session = await get_or_create_session(
            db=db,
            session_id=session_id,
            patient_id=request.patient_id,
            first_message=request.message
        )
        
        # Build patient context
        patient_context = build_context_from_data(request)
        
        # Get conversation history
        conversation_history = await get_session_history(db, session.id)
        
        # Build chat messages
        messages = build_chat_messages(
            user_message=request.message,
            patient_context=patient_context,
            conversation_history=conversation_history
        )
        
        # Stream generator
        async def event_generator():
            try:
                async for event in generate_response_with_tools(messages, enable_streaming=True):
                    # Format as SSE
                    event_type = event.get("type", "message")
                    event_data = event.get("data")
                    
                    # Serialize event data
                    sse_data = json.dumps({
                        "type": event_type,
                        "data": event_data,
                        "timestamp": event.get("timestamp")
                    })
                    
                    yield f"data: {sse_data}\n\n"
                    
                    # If done, close stream
                    if event_type == "done":
                        break
            
            except Exception as e:
                logger.error(f"Error in stream generator: {str(e)}")
                error_event = json.dumps({
                    "type": "error",
                    "data": f"Error: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                yield f"data: {error_event}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable proxy buffering
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in chat/stream endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while setting up the stream"
        )


@router.post("/artifacts/generate-pdf")
async def generate_artifact_pdf(
    artifact_data: dict,
    db: Session = Depends(get_db)
):
    """
    Generate a PDF from artifact data.
    
    **Request Body:** Artifact structure (from chat response artifacts field)
    
    **Returns:** PDF file as downloadable binary
    
    **Note:** Requires WeasyPrint system libraries. Use /artifacts/to-html if PDF not available.
    """
    try:
        # Import artifacts locally
        from . import artifacts
        
        # Check if PDF generation is available
        if not artifacts.is_pdf_available():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    "PDF generation not available. WeasyPrint system libraries not installed. "
                    "Install with: brew install pango cairo gdk-pixbuf libffi (macOS). "
                    "Use /artifacts/to-html for HTML output instead."
                )
            )
        
        # Generate PDF
        pdf_bytes = artifacts.artifact_to_pdf(artifact_data)
        
        # Return as downloadable file
        from fastapi.responses import Response
        
        filename = artifact_data.get("title", "medical_document").replace(" ", "_")
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.pdf"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating PDF: {str(e)}"
        )


@router.post("/artifacts/to-html")
async def artifact_to_html_endpoint(
    artifact_data: dict,
    db: Session = Depends(get_db)
):
    """
    Convert artifact to HTML for display.
    
    **Request Body:** Artifact structure
    
    **Returns:** HTML string with styling
    """
    try:
        # Import artifacts locally
        from . import artifacts
        
        html_content = artifacts.artifact_to_html(artifact_data)
        
        return {
            "html": html_content,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error converting to HTML: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting to HTML: {str(e)}"
        )

