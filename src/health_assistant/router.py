from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session
from typing import Optional, List
import logging

from src.database import get_db
from src.health_assistant.schemas import (
    ChatRequest,
    ChatResponse,
    HealthSessionResponse,
    SessionListResponse,
    ConversationResponse,
    HealthMessageResponse,
)
from src.health_assistant.services import HealthAssistantService
from src.health_assistant.model_service import model_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health-assistant", tags=["Health Assistant"])


@router.get("/")
async def health_assistant_root():
    """Health assistant root endpoint"""
    return {
        "message": "Health Assistant API - Ready to help with your health queries",
        "endpoints": {
            "chat": "/chat",
            "sessions": "/sessions",
            "health": "/health",
        },
    }


@router.get("/health")
async def health_check():
    """Check if AI models are accessible via API"""
    model_status = model_service.health_check()

    # Check both text and vision models
    if not model_status["text_model_ready"]:
        return {
            "status": "degraded",
            "models": model_status,
            "message": "Text model not accessible",
        }

    if not model_status["vision_model_ready"]:
        return {
            "status": "degraded",
            "models": model_status,
            "message": "Vision model not accessible",
        }

    return {
        "status": "healthy",
        "models": model_status,
        "message": "All models accessible via HuggingFace API",
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Main chat endpoint - handles both text-only and image+text queries.

    - If image is provided: Uses Qwen2-VL for vision-language analysis
    - If text only: Uses Qwen2.5-7B-Instruct for conversation
    - Automatically manages sessions (creates new or continues existing)

    Args:
        chat_request: Chat request with prompt, optional session_id, and optional image
        db: Database session

    Returns:
        ChatResponse with AI-generated response and session information
    """
    try:
        # Process image if provided
        image = None
        if chat_request.image_base64:
            try:
                image = model_service.process_image_from_base64(
                    chat_request.image_base64
                )
                logger.info("Image processed successfully")
            except Exception as e:
                logger.error(f"Failed to process image: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image format. Please provide a valid base64 encoded image.",
                )

        # Process chat message
        result = await HealthAssistantService.process_chat_message(
            db=db,
            prompt=chat_request.prompt,
            session_id=chat_request.session_id,
            user_id=chat_request.user_id,
            image=image,
            max_tokens=chat_request.max_tokens,
            temperature=chat_request.temperature,
        )

        return ChatResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your request: {str(e)}",
        )


@router.post("/chat/upload", response_model=ChatResponse)
async def chat_with_upload(
    prompt: str = Form(...),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    max_tokens: int = Form(512),
    temperature: float = Form(0.7),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Alternative chat endpoint that accepts file upload instead of base64.
    Useful for direct file uploads from frontend.

    Args:
        prompt: User's query
        session_id: Optional session ID
        user_id: Optional user ID
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        image: Optional uploaded image file
        db: Database session

    Returns:
        ChatResponse with AI-generated response
    """
    try:
        # Process image if uploaded
        pil_image = None
        if image:
            try:
                image_bytes = await image.read()
                pil_image = model_service.process_image_from_bytes(image_bytes)
                logger.info(f"Image uploaded and processed: {image.filename}")
            except Exception as e:
                logger.error(f"Failed to process uploaded image: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image file. Please upload a valid image.",
                )

        # Process chat message
        result = await HealthAssistantService.process_chat_message(
            db=db,
            prompt=prompt,
            session_id=session_id,
            user_id=user_id,
            image=pil_image,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return ChatResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat upload endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your request: {str(e)}",
        )


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    user_id: str,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    Get all sessions for a user.

    Args:
        user_id: User ID
        active_only: Only return active sessions (default: True)
        db: Database session

    Returns:
        List of sessions
    """
    try:
        sessions = HealthAssistantService.get_user_sessions(
            db=db,
            user_id=user_id,
            active_only=active_only,
        )

        return SessionListResponse(
            sessions=[HealthSessionResponse.model_validate(s) for s in sessions],
            total=len(sessions),
        )

    except Exception as e:
        logger.error(f"Error getting sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving sessions: {str(e)}",
        )


@router.get("/sessions/{session_id}", response_model=ConversationResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a specific session with all messages.

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Session with messages
    """
    try:
        result = HealthAssistantService.get_session_with_messages(
            db=db,
            session_id=session_id,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return ConversationResponse(
            session=HealthSessionResponse.model_validate(result["session"]),
            messages=[
                HealthMessageResponse.model_validate(m) for m in result["messages"]
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the session: {str(e)}",
        )


@router.delete("/sessions/{session_id}", response_model=HealthSessionResponse)
async def end_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    End/close a session.

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Updated session
    """
    try:
        session = HealthAssistantService.end_session(
            db=db,
            session_id=session_id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return HealthSessionResponse.model_validate(session)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while ending the session: {str(e)}",
        )
