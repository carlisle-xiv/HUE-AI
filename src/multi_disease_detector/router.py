"""
FastAPI router for Multi Disease Detector endpoints.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
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
    message: str = Form(...),
    patient_id: Optional[str] = Form(None),
    consultation_data: Optional[str] = Form(None),
    vitals_data: Optional[str] = Form(None),
    habits_data: Optional[str] = Form(None),
    conditions_data: Optional[str] = Form(None),
    ai_consultation_data: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> ChatResponse:
    """
    Main chat endpoint for conversational AI health consultant.
    
    **Query Parameters:**
    - **session-id** (optional): Session UUID for ongoing conversations. Omit for new sessions.
    
    **Request Body (multipart/form-data - only 'message' is required):**
    - **message**: User's message/prompt (REQUIRED)
    - **patient_id**: Patient UUID for tracking
    - **image**: Optional medical image (JPEG, PNG, WEBP, max 20MB) 
    - **consultation_data**: Recent consultation information as JSON string
    - **vitals_data**: Latest vital signs as JSON string
    - **habits_data**: Patient habits tracking as JSON string
    - **conditions_data**: Active medical conditions as JSON string
    - **ai_consultation_data**: Previous AI consultation data as JSON string
    
    **Returns:** AI-generated response with risk assessment and medical disclaimer.
    
    **Note:** When uploading an image, use multipart/form-data encoding.
    """
    try:
        # Import vision service
        from .vision_service import analyze_medical_image
        from .image_utils import ImageValidationError
        
        # Process image if provided
        image_interpretation = None
        if image:
            try:
                logger.info(f"Processing uploaded image: {image.filename}")
                image_bytes = await image.read()
                image_interpretation = await analyze_medical_image(
                    image_bytes=image_bytes,
                    user_context=message[:200],  # Use truncated message as context
                    filename=image.filename
                )
                logger.info("Image analysis completed successfully")
            except ImageValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image validation failed: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process image: {str(e)}"
                )
        
        # Parse JSON strings from form data
        parsed_consultation_data = json.loads(consultation_data) if consultation_data else None
        parsed_vitals_data = json.loads(vitals_data) if vitals_data else None
        parsed_habits_data = json.loads(habits_data) if habits_data else None
        parsed_conditions_data = json.loads(conditions_data) if conditions_data else None
        parsed_ai_consultation_data = json.loads(ai_consultation_data) if ai_consultation_data else None
        
        # Parse patient_id if provided
        parsed_patient_id = UUID(patient_id) if patient_id else None
        
        # Build ChatRequest object
        request = ChatRequest(
            message=message,
            patient_id=parsed_patient_id,
            session_id=session_id,
            consultation_data=parsed_consultation_data,
            vitals_data=parsed_vitals_data,
            habits_data=parsed_habits_data,
            conditions_data=parsed_conditions_data,
            ai_consultation_data=parsed_ai_consultation_data
        )
        
        # Process chat request with optional image interpretation
        response = await process_chat_request(
            db=db, 
            request=request,
            image_interpretation=image_interpretation
        )
        return response
        
    except HTTPException:
        raise
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
    message: str = Form(...),
    patient_id: Optional[str] = Form(None),
    consultation_data: Optional[str] = Form(None),
    vitals_data: Optional[str] = Form(None),
    habits_data: Optional[str] = Form(None),
    conditions_data: Optional[str] = Form(None),
    ai_consultation_data: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
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
    - **Analyze medical images with GPT-5 vision**
    
    **Query Parameters:**
    - **session-id** (optional): Session UUID for ongoing conversations
    
    **Request Body (multipart/form-data):**
    - **message**: User's message/prompt (REQUIRED)
    - **patient_id**: Patient UUID for tracking
    - **image**: Optional medical image (JPEG, PNG, WEBP, max 20MB)
    - All context data fields as JSON strings (optional)
    
    **Returns:** 
    - AI-generated response with risk assessment
    - List of tools used
    - Thinking process summary
    - References to any generated artifacts
    """
    try:
        # Import vision service
        from .vision_service import analyze_medical_image
        from .image_utils import ImageValidationError
        
        # Process image if provided
        image_interpretation = None
        if image:
            try:
                logger.info(f"Processing uploaded image: {image.filename}")
                image_bytes = await image.read()
                image_interpretation = await analyze_medical_image(
                    image_bytes=image_bytes,
                    user_context=message[:200],
                    filename=image.filename
                )
                logger.info("Image analysis completed successfully")
            except ImageValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image validation failed: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process image: {str(e)}"
                )
        
        # Parse JSON strings from form data
        parsed_consultation_data = json.loads(consultation_data) if consultation_data else None
        parsed_vitals_data = json.loads(vitals_data) if vitals_data else None
        parsed_habits_data = json.loads(habits_data) if habits_data else None
        parsed_conditions_data = json.loads(conditions_data) if conditions_data else None
        parsed_ai_consultation_data = json.loads(ai_consultation_data) if ai_consultation_data else None
        parsed_patient_id = UUID(patient_id) if patient_id else None
        
        # Build ChatRequest object
        request = ChatRequest(
            message=message,
            patient_id=parsed_patient_id,
            session_id=session_id,
            consultation_data=parsed_consultation_data,
            vitals_data=parsed_vitals_data,
            habits_data=parsed_habits_data,
            conditions_data=parsed_conditions_data,
            ai_consultation_data=parsed_ai_consultation_data
        )
        
        # Process with tools and image interpretation
        response = await process_chat_request_with_tools(
            db=db, 
            request=request,
            image_interpretation=image_interpretation
        )
        return response
        
    except HTTPException:
        raise
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
    message: str = Form(...),
    patient_id: Optional[str] = Form(None),
    consultation_data: Optional[str] = Form(None),
    vitals_data: Optional[str] = Form(None),
    habits_data: Optional[str] = Form(None),
    conditions_data: Optional[str] = Form(None),
    ai_consultation_data: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Streaming chat endpoint that shows AI's thinking process in real-time.
    
    Returns Server-Sent Events (SSE) with different event types:
    - **image_validation**: Image validation progress (if image provided)
    - **image_processing**: Image encoding/preparation (if image provided)
    - **vision_analysis**: GPT-5 analyzing image (if image provided)
    - **vision_complete**: Image analysis results (if image provided)
    - **thinking**: AI's reasoning process
    - **tool_call**: When AI decides to use a tool
    - **tool_result**: Results from tool execution
    - **content**: AI's response content (streamed token by token)
    - **done**: Final completion event
    - **error**: Error occurred
    
    **Query Parameters:**
    - **session-id** (optional): Session UUID for ongoing conversations
    
    **Request Body (multipart/form-data):**
    - **message**: User's message/prompt (REQUIRED)
    - **image**: Optional medical image (JPEG, PNG, WEBP, max 20MB)
    - All other fields same as /chat endpoint
    
    **Usage Example (JavaScript):**
    ```javascript
    const formData = new FormData();
    formData.append('message', 'What is this rash?');
    formData.append('image', imageFile);
    
    const response = await fetch('/api/v1/multi-disease-detector/chat/stream', {
        method: 'POST',
        body: formData
    });
    
    const reader = response.body.getReader();
    // Process SSE stream...
    ```
    """
    try:
        # Import vision service
        from .vision_service import analyze_medical_image_streaming
        from .image_utils import ImageValidationError
        
        # Parse JSON strings from form data
        parsed_consultation_data = json.loads(consultation_data) if consultation_data else None
        parsed_vitals_data = json.loads(vitals_data) if vitals_data else None
        parsed_habits_data = json.loads(habits_data) if habits_data else None
        parsed_conditions_data = json.loads(conditions_data) if conditions_data else None
        parsed_ai_consultation_data = json.loads(ai_consultation_data) if ai_consultation_data else None
        parsed_patient_id = UUID(patient_id) if patient_id else None
        
        # Build ChatRequest object
        request = ChatRequest(
            message=message,
            patient_id=parsed_patient_id,
            session_id=session_id,
            consultation_data=parsed_consultation_data,
            vitals_data=parsed_vitals_data,
            habits_data=parsed_habits_data,
            conditions_data=parsed_conditions_data,
            ai_consultation_data=parsed_ai_consultation_data
        )
        
        # Get or create session
        session = await get_or_create_session(
            db=db,
            session_id=session_id,
            patient_id=request.patient_id,
            first_message=request.message
        )
        
        # Read image bytes BEFORE creating generator (while file handle is open)
        image_bytes = None
        image_filename = None
        if image:
            try:
                logger.info(f"Reading uploaded image: {image.filename} (content_type: {image.content_type})")
                image_bytes = await image.read()
                image_filename = image.filename
                logger.info(f"Successfully read image: {len(image_bytes)} bytes")
            except Exception as e:
                logger.error(f"Error reading image file '{image.filename}': {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to read image file: {str(e)}"
                )
        
        # Stream generator
        async def event_generator():
            try:
                image_interpretation = None
                
                # Step 1: Process image if provided (with streaming events)
                if image_bytes:
                    logger.info(f"Processing image in stream: {image_filename}")
                    async for vision_event in analyze_medical_image_streaming(
                        image_bytes=image_bytes,
                        user_context=message[:200],
                        filename=image_filename
                    ):
                        # Relay vision events
                        sse_data = json.dumps(vision_event)
                        yield f"data: {sse_data}\n\n"
                        
                        # Capture final interpretation
                        if vision_event.get("type") == "vision_complete":
                            image_interpretation = vision_event.get("data")
                        
                        # Stop if error
                        if vision_event.get("type") == "error":
                            return
                
                # Step 2: Build patient context (including image interpretation)
                patient_context = build_context_from_data(request, image_interpretation)
                
                # Step 3: Get conversation history
                conversation_history = await get_session_history(db, session.id)
                
                # Step 4: Build chat messages
                messages = build_chat_messages(
                    user_message=request.message,
                    patient_context=patient_context,
                    conversation_history=conversation_history
                )
                
                # Step 5: Stream AI response with tools
                async for event in generate_response_with_tools(messages, enable_streaming=True):
                    # Format as SSE
                    event_type = event.get("type", "message")
                    event_data = event.get("data")
                    
                    # Add session_id to done event for conversation continuity
                    if event_type == "done" and isinstance(event_data, dict):
                        event_data["session_id"] = str(session.id)
                    
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
        
    except HTTPException:
        raise
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

