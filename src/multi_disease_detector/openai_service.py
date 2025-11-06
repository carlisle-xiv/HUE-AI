"""
Service layer for OpenAI-compliant chat completions endpoint.
Handles message conversion, image processing, tool calling, and streaming.
"""

import base64
import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from uuid import UUID, uuid4

from sqlmodel import Session

from .openai_schemas import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIStreamChunk,
    ChatMessage,
    ResponseMessage,
    ChatChoice,
    StreamChoice,
    StreamDelta,
    UsageInfo,
    TextContent,
    ImageContent,
    ToolCall,
)
from .schemas import ChatRequest, ChatResponse, ChatResponseWithArtifacts
from .service import (
    get_or_create_session,
    build_context_from_data,
    get_session_history,
    build_chat_messages,
    generate_response_with_tools,
    calculate_risk_assessment,
    save_chat_exchange_with_metadata,
    DISCLAIMER_TEXT,
)
from .vision_service import analyze_medical_image
from .image_utils import ImageValidationError

# Configure logging
logger = logging.getLogger(__name__)


def extract_images_from_messages(messages: List[ChatMessage]) -> Tuple[List[bytes], List[ChatMessage]]:
    """
    Extract base64 images from OpenAI message format and convert to clean messages.
    
    Args:
        messages: List of ChatMessage objects
        
    Returns:
        Tuple of (image_bytes_list, cleaned_messages)
    """
    images = []
    cleaned_messages = []
    
    for msg in messages:
        if msg.role == "user" and isinstance(msg.content, list):
            # Message has structured content (text + images)
            text_parts = []
            
            for item in msg.content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    
                    if item_type == "text":
                        text_parts.append(item.get("text", ""))
                    
                    elif item_type == "image_url":
                        # Extract image
                        image_url = item.get("image_url", {})
                        if isinstance(image_url, dict):
                            url = image_url.get("url", "")
                        else:
                            url = str(image_url)
                        
                        # Check if it's base64 data URI
                        if url.startswith("data:image/"):
                            try:
                                # Extract base64 data
                                # Format: data:image/jpeg;base64,<base64_data>
                                match = re.match(r'data:image/[^;]+;base64,(.+)', url)
                                if match:
                                    base64_data = match.group(1)
                                    image_bytes = base64.b64decode(base64_data)
                                    images.append(image_bytes)
                                    logger.info(f"Extracted image from message: {len(image_bytes)} bytes")
                            except Exception as e:
                                logger.error(f"Failed to decode base64 image: {str(e)}")
            
            # Create cleaned message with just text content
            if text_parts:
                cleaned_msg = ChatMessage(
                    role=msg.role,
                    content=" ".join(text_parts),
                    name=msg.name
                )
                cleaned_messages.append(cleaned_msg)
        else:
            # Regular message, keep as-is
            cleaned_messages.append(msg)
    
    return images, cleaned_messages


def convert_openai_to_internal_format(
    request: OpenAIChatRequest,
    image_interpretation: Optional[Dict[str, Any]] = None
) -> Tuple[List[dict], Optional[ChatRequest]]:
    """
    Convert OpenAI format messages to internal format for processing.
    
    Args:
        request: OpenAI chat request
        image_interpretation: Optional image analysis results
        
    Returns:
        Tuple of (internal_messages, chat_request_for_context)
    """
    # Extract patient context if provided
    patient_context_data = None
    if request.patient_context:
        pc = request.patient_context
        patient_context_data = ChatRequest(
            message="",  # Will be filled from last user message
            patient_id=pc.patient_id,
            session_id=pc.session_id,
            consultation_data=pc.consultation_data,
            vitals_data=pc.vitals_data,
            habits_data=pc.habits_data,
            conditions_data=pc.conditions_data,
            ai_consultation_data=pc.ai_consultation_data,
        )
    
    # Convert messages to internal format
    internal_messages = []
    
    for msg in request.messages:
        # Get content as string
        if isinstance(msg.content, str):
            content = msg.content
        elif isinstance(msg.content, list):
            # Join text parts
            text_parts = []
            for item in msg.content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            content = " ".join(text_parts)
        else:
            content = str(msg.content) if msg.content else ""
        
        # Map role
        role_mapping = {
            "system": "system",
            "user": "user",
            "assistant": "assistant",
            "tool": "tool"
        }
        
        internal_msg = {
            "role": role_mapping.get(msg.role, "user"),
            "content": content
        }
        
        # Add tool calls if present
        if msg.tool_calls:
            internal_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in msg.tool_calls
            ]
        
        # Add tool_call_id for tool messages
        if msg.role == "tool" and msg.tool_call_id:
            internal_msg["tool_call_id"] = msg.tool_call_id
        
        internal_messages.append(internal_msg)
    
    # Add image interpretation to context if available
    if image_interpretation and patient_context_data:
        # Image interpretation will be added to system message via build_context_from_data
        pass
    
    return internal_messages, patient_context_data


def build_openai_response(
    completion_id: str,
    model: str,
    content: str,
    finish_reason: str = "stop",
    session_id: Optional[UUID] = None,
    tool_calls: Optional[List[ToolCall]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0
) -> OpenAIChatResponse:
    """
    Build OpenAI-compliant response from internal data.
    
    Args:
        completion_id: Unique completion ID
        model: Model name
        content: Response content
        finish_reason: Why generation stopped
        session_id: Session ID for continuity
        tool_calls: Any tool calls made
        metadata: Additional metadata (risk assessment, etc.)
        prompt_tokens: Estimated prompt tokens
        completion_tokens: Estimated completion tokens
        
    Returns:
        OpenAI-compliant response
    """
    response_message = ResponseMessage(
        role="assistant",
        content=content,
        tool_calls=tool_calls,
        metadata=metadata
    )
    
    choice = ChatChoice(
        index=0,
        message=response_message,
        finish_reason=finish_reason
    )
    
    usage = UsageInfo(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens
    )
    
    return OpenAIChatResponse(
        id=completion_id,
        object="chat.completion",
        created=int(datetime.utcnow().timestamp()),
        model=model,
        choices=[choice],
        usage=usage,
        session_id=str(session_id) if session_id else None
    )


def build_openai_stream_chunk(
    completion_id: str,
    model: str,
    delta_content: Optional[str] = None,
    finish_reason: Optional[str] = None,
    role: Optional[str] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    event_type: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None
) -> OpenAIStreamChunk:
    """
    Build OpenAI-compliant streaming chunk.
    
    Args:
        completion_id: Unique completion ID (same across all chunks)
        model: Model name
        delta_content: Incremental content
        finish_reason: Finish reason (only in final chunk)
        role: Role (only in first chunk)
        tool_calls: Partial tool calls
        event_type: Custom event type (HUE AI extension)
        event_data: Custom event data (HUE AI extension)
        
    Returns:
        OpenAI stream chunk
    """
    delta = StreamDelta(
        role=role,
        content=delta_content,
        tool_calls=tool_calls
    )
    
    choice = StreamChoice(
        index=0,
        delta=delta,
        finish_reason=finish_reason
    )
    
    return OpenAIStreamChunk(
        id=completion_id,
        object="chat.completion.chunk",
        created=int(datetime.utcnow().timestamp()),
        model=model,
        choices=[choice],
        event_type=event_type,
        event_data=event_data
    )


async def process_openai_chat_request(
    db: Session,
    request: OpenAIChatRequest
) -> OpenAIChatResponse:
    """
    Process OpenAI-compliant chat request (non-streaming).
    
    Args:
        db: Database session
        request: OpenAI chat request
        
    Returns:
        OpenAI-compliant response
        
    Raises:
        HTTPException: On validation or processing errors
    """
    try:
        completion_id = f"chatcmpl-{uuid4().hex[:12]}"
        logger.info(f"Processing OpenAI chat request: {completion_id}")
        
        # Step 1: Extract images from messages
        image_bytes_list, cleaned_messages = extract_images_from_messages(request.messages)
        
        # Step 2: Process first image if present (we'll use the first one)
        image_interpretation = None
        if image_bytes_list:
            try:
                logger.info(f"Processing {len(image_bytes_list)} image(s)")
                # Use first image for now (can be enhanced to handle multiple)
                image_bytes = image_bytes_list[0]
                
                # Get user context from last user message
                user_context = ""
                for msg in reversed(cleaned_messages):
                    if msg.role == "user" and isinstance(msg.content, str):
                        user_context = msg.content[:200]
                        break
                
                image_interpretation = await analyze_medical_image(
                    image_bytes=image_bytes,
                    user_context=user_context,
                    filename="uploaded_image.jpg"
                )
                logger.info("Image analysis completed")
            except ImageValidationError as e:
                logger.error(f"Image validation failed: {str(e)}")
                # Continue without image - let the AI respond with text only
            except Exception as e:
                logger.error(f"Image processing failed: {str(e)}")
                # Continue without image
        
        # Step 3: Update request with cleaned messages
        request_copy = request.model_copy()
        request_copy.messages = cleaned_messages
        
        # Step 4: Convert to internal format
        internal_messages, patient_context_data = convert_openai_to_internal_format(
            request_copy,
            image_interpretation
        )
        
        # Step 5: Handle session management
        session_id = None
        patient_id = None
        if request.patient_context:
            session_id = request.patient_context.session_id
            patient_id = request.patient_context.patient_id
        
        # Get last user message for session creation
        last_user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                if isinstance(msg.content, str):
                    last_user_message = msg.content
                elif isinstance(msg.content, list):
                    text_parts = [
                        item.get("text", "")
                        for item in msg.content
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    last_user_message = " ".join(text_parts)
                break
        
        session = None
        if patient_id:
            session = await get_or_create_session(
                db=db,
                session_id=session_id,
                patient_id=patient_id,
                first_message=last_user_message or "New conversation"
            )
        
        # Step 6: Build patient context
        patient_context_str = ""
        if patient_context_data:
            patient_context_str = build_context_from_data(patient_context_data, image_interpretation)
        
        # Step 7: Process with tools if enabled
        tools_enabled = request.tools is not None and len(request.tools) > 0
        
        if tools_enabled:
            # Use tool-enabled processing
            final_message = ""
            tools_used = []
            thinking_steps = []
            
            async for event in generate_response_with_tools(internal_messages, enable_streaming=False):
                event_type = event.get("type")
                
                if event_type == "thinking":
                    thinking_steps.append(event.get("data"))
                elif event_type == "content":
                    final_message += event.get("data", "")
                elif event_type == "done":
                    data = event.get("data", {})
                    final_message = data.get("message", final_message)
                    tools_used = data.get("tools_used", [])
            
            # Calculate risk assessment
            risk_level, should_see_doctor = calculate_risk_assessment(
                message=final_message,
                patient_context=patient_context_str
            )
            
            # Save to database if we have a session
            if session:
                await save_chat_exchange_with_metadata(
                    db=db,
                    session_id=session.id,
                    user_message=last_user_message,
                    assistant_message=final_message,
                    risk_assessment=risk_level,
                    tools_used=tools_used,
                    thinking_summary=" → ".join(thinking_steps[:3]) if thinking_steps else None,
                    image_interpretation=image_interpretation
                )
            
            # Build metadata
            metadata = {
                "risk_assessment": risk_level,
                "should_see_doctor": should_see_doctor,
                "tools_used": tools_used,
                "disclaimer": DISCLAIMER_TEXT
            }
            
            # Estimate tokens (rough estimation)
            prompt_tokens = sum(len(str(msg.get("content", "")).split()) for msg in internal_messages) * 1.3
            completion_tokens = len(final_message.split()) * 1.3
            
            return build_openai_response(
                completion_id=completion_id,
                model=request.model,
                content=final_message,
                finish_reason="stop",
                session_id=session.id if session else None,
                metadata=metadata,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens)
            )
        else:
            # Simple generation without tools
            from .service import generate_response
            
            ai_message = await generate_response(internal_messages)
            
            # Calculate risk assessment
            risk_level, should_see_doctor = calculate_risk_assessment(
                message=ai_message,
                patient_context=patient_context_str
            )
            
            # Save to database if we have a session
            if session:
                from .service import save_chat_exchange
                await save_chat_exchange(
                    db=db,
                    session_id=session.id,
                    user_message=last_user_message,
                    assistant_message=ai_message,
                    risk_assessment=risk_level
                )
            
            # Build metadata
            metadata = {
                "risk_assessment": risk_level,
                "should_see_doctor": should_see_doctor,
                "disclaimer": DISCLAIMER_TEXT
            }
            
            # Estimate tokens
            prompt_tokens = sum(len(str(msg.get("content", "")).split()) for msg in internal_messages) * 1.3
            completion_tokens = len(ai_message.split()) * 1.3
            
            return build_openai_response(
                completion_id=completion_id,
                model=request.model,
                content=ai_message,
                finish_reason="stop",
                session_id=session.id if session else None,
                metadata=metadata,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens)
            )
    
    except Exception as e:
        logger.error(f"Error processing OpenAI chat request: {str(e)}")
        raise


async def process_openai_chat_request_streaming(
    db: Session,
    request: OpenAIChatRequest
) -> AsyncGenerator[str, None]:
    """
    Process OpenAI-compliant chat request with streaming.
    Yields SSE-formatted chunks in OpenAI format.
    
    Args:
        db: Database session
        request: OpenAI chat request with stream=True
        
    Yields:
        SSE-formatted strings: "data: {json}\n\n"
    """
    try:
        completion_id = f"chatcmpl-{uuid4().hex[:12]}"
        model = request.model
        
        logger.info(f"Processing OpenAI streaming chat request: {completion_id}")
        
        # Step 1: Extract images from messages
        image_bytes_list, cleaned_messages = extract_images_from_messages(request.messages)
        
        # Step 2: Process first image if present
        image_interpretation = None
        if image_bytes_list:
            try:
                logger.info(f"Processing {len(image_bytes_list)} image(s) in stream")
                image_bytes = image_bytes_list[0]
                
                # Get user context
                user_context = ""
                for msg in reversed(cleaned_messages):
                    if msg.role == "user" and isinstance(msg.content, str):
                        user_context = msg.content[:200]
                        break
                
                # Stream image processing events
                from .vision_service import analyze_medical_image_streaming
                
                async for vision_event in analyze_medical_image_streaming(
                    image_bytes=image_bytes,
                    user_context=user_context,
                    filename="uploaded_image.jpg"
                ):
                    # Convert to OpenAI stream chunk with custom event
                    event_type = vision_event.get("type")
                    event_data = vision_event.get("data")
                    
                    chunk = build_openai_stream_chunk(
                        completion_id=completion_id,
                        model=model,
                        event_type=event_type,
                        event_data={"vision_event": event_data}
                    )
                    
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    
                    # Capture interpretation
                    if event_type == "vision_complete":
                        image_interpretation = event_data
                    
                    # Stop if error
                    if event_type == "error":
                        return
                        
            except Exception as e:
                logger.error(f"Image processing error in stream: {str(e)}")
                # Send error chunk
                chunk = build_openai_stream_chunk(
                    completion_id=completion_id,
                    model=model,
                    event_type="error",
                    event_data={"error": str(e)}
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
        
        # Step 3: Update request with cleaned messages
        request_copy = request.model_copy()
        request_copy.messages = cleaned_messages
        
        # Step 4: Convert to internal format
        internal_messages, patient_context_data = convert_openai_to_internal_format(
            request_copy,
            image_interpretation
        )
        
        # Step 5: Handle session management
        session_id = None
        patient_id = None
        if request.patient_context:
            session_id = request.patient_context.session_id
            patient_id = request.patient_context.patient_id
        
        # Get last user message
        last_user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                if isinstance(msg.content, str):
                    last_user_message = msg.content
                elif isinstance(msg.content, list):
                    text_parts = [
                        item.get("text", "")
                        for item in msg.content
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    last_user_message = " ".join(text_parts)
                break
        
        session = None
        if patient_id:
            session = await get_or_create_session(
                db=db,
                session_id=session_id,
                patient_id=patient_id,
                first_message=last_user_message or "New conversation"
            )
        
        # Step 6: Send initial chunk with role
        initial_chunk = build_openai_stream_chunk(
            completion_id=completion_id,
            model=model,
            role="assistant"
        )
        yield f"data: {initial_chunk.model_dump_json()}\n\n"
        
        # Step 7: Stream AI response
        accumulated_content = ""
        tools_used = []
        thinking_steps = []
        
        async for event in generate_response_with_tools(internal_messages, enable_streaming=True):
            event_type = event.get("type")
            event_data = event.get("data")
            
            if event_type == "thinking":
                # Send as custom event
                chunk = build_openai_stream_chunk(
                    completion_id=completion_id,
                    model=model,
                    event_type="thinking",
                    event_data={"thinking": event_data}
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
                thinking_steps.append(event_data)
            
            elif event_type == "tool_call":
                # Send tool call event
                chunk = build_openai_stream_chunk(
                    completion_id=completion_id,
                    model=model,
                    event_type="tool_call",
                    event_data=event_data
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
            
            elif event_type == "tool_result":
                # Send tool result event
                chunk = build_openai_stream_chunk(
                    completion_id=completion_id,
                    model=model,
                    event_type="tool_result",
                    event_data=event_data
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
                
                if isinstance(event_data, dict):
                    tool_name = event_data.get("tool_name")
                    if tool_name:
                        tools_used.append(tool_name)
            
            elif event_type == "content":
                # Send content delta
                accumulated_content += event_data
                chunk = build_openai_stream_chunk(
                    completion_id=completion_id,
                    model=model,
                    delta_content=event_data
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
            
            elif event_type == "done":
                # Final chunk with finish_reason
                if isinstance(event_data, dict):
                    tools_used = event_data.get("tools_used", tools_used)
                
                # Calculate risk assessment
                patient_context_str = ""
                if patient_context_data:
                    patient_context_str = build_context_from_data(patient_context_data, image_interpretation)
                
                risk_level, should_see_doctor = calculate_risk_assessment(
                    message=accumulated_content,
                    patient_context=patient_context_str
                )
                
                # Save to database
                if session:
                    await save_chat_exchange_with_metadata(
                        db=db,
                        session_id=session.id,
                        user_message=last_user_message,
                        assistant_message=accumulated_content,
                        risk_assessment=risk_level,
                        tools_used=tools_used,
                        thinking_summary=" → ".join(thinking_steps[:3]) if thinking_steps else None,
                        image_interpretation=image_interpretation
                    )
                
                # Send final chunk
                final_chunk = build_openai_stream_chunk(
                    completion_id=completion_id,
                    model=model,
                    finish_reason="stop",
                    event_type="done",
                    event_data={
                        "session_id": str(session.id) if session else None,
                        "risk_assessment": risk_level,
                        "should_see_doctor": should_see_doctor,
                        "tools_used": tools_used,
                        "disclaimer": DISCLAIMER_TEXT
                    }
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                
                # Send [DONE] marker (OpenAI standard)
                yield "data: [DONE]\n\n"
                break
        
    except Exception as e:
        logger.error(f"Error in OpenAI streaming: {str(e)}")
        # Send error chunk
        error_chunk = build_openai_stream_chunk(
            completion_id=completion_id if 'completion_id' in locals() else "error",
            model=model if 'model' in locals() else "unknown",
            event_type="error",
            event_data={"error": str(e)}
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"

