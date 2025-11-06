"""
Service layer for simplified chat endpoint.
Converts between simplified client format and internal OpenAI format.
"""

import base64
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from uuid import UUID

from sqlmodel import Session

from .simplified_schemas import SimplifiedChatRequest, SimplifiedChatResponse, SimplifiedStreamEvent
from .openai_schemas import (
    OpenAIChatRequest,
    ChatMessage,
    PatientContext,
    TextContent,
    ImageContent,
    ImageUrl,
)
from .openai_service import process_openai_chat_request, process_openai_chat_request_streaming
from .tools import TOOL_DEFINITIONS

# Configure logging
logger = logging.getLogger(__name__)

# Internal configuration (hidden from clients)
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TOP_P = 0.9
SYSTEM_MESSAGE = (
    "You are an AI health consultant assisting patients with health-related questions. "
    "You provide helpful, empathetic, and medically-informed responses. "
    "Always remind users that you are an AI assistant and they should consult healthcare professionals for proper diagnosis and treatment. "
    "Be conversational and supportive while maintaining medical accuracy."
)


def convert_simplified_to_openai_format(
    request: SimplifiedChatRequest,
    session_id: Optional[UUID] = None
) -> OpenAIChatRequest:
    """
    Convert simplified request to OpenAI format.
    
    Args:
        request: Simplified chat request
        session_id: Optional session ID from query parameter
        
    Returns:
        OpenAI-compliant chat request
    """
    # Build messages array
    messages = []
    
    # Add system message
    messages.append(ChatMessage(
        role="system",
        content=SYSTEM_MESSAGE
    ))
    
    # Build user message
    if request.image:
        # Message with image - use content array
        user_content = [
            TextContent(type="text", text=request.message)
        ]
        
        # Add image
        # Check if image already has data URI prefix
        if request.image.startswith("data:image/"):
            image_url = request.image
        else:
            # Assume it's raw base64, add JPEG prefix
            image_url = f"data:image/jpeg;base64,{request.image}"
        
        user_content.append(
            ImageContent(
                type="image_url",
                image_url=ImageUrl(url=image_url)
            )
        )
        
        messages.append(ChatMessage(
            role="user",
            content=user_content
        ))
    else:
        # Simple text message
        messages.append(ChatMessage(
            role="user",
            content=request.message
        ))
    
    # Build patient context
    patient_context = None
    if any([
        request.patient_id,
        request.consultation_data,
        request.vitals_data,
        request.habits_data,
        request.conditions_data,
        request.ai_consultation_data
    ]):
        patient_context = PatientContext(
            patient_id=request.patient_id,
            session_id=session_id,
            consultation_data=request.consultation_data,
            vitals_data=request.vitals_data,
            habits_data=request.habits_data,
            conditions_data=request.conditions_data,
            ai_consultation_data=request.ai_consultation_data
        )
    
    # Build tools array (all available tools)
    tools = [
        {
            "type": "function",
            "function": {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "parameters": tool["function"]["parameters"]
            }
        }
        for tool in TOOL_DEFINITIONS
    ]
    
    # Create OpenAI request
    openai_request = OpenAIChatRequest(
        messages=messages,
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        temperature=DEFAULT_TEMPERATURE,
        top_p=DEFAULT_TOP_P,
        stream=request.stream,
        tools=tools,
        tool_choice="auto",
        patient_context=patient_context
    )
    
    return openai_request


def convert_openai_to_simplified_response(
    openai_response: Any,
    session_id: UUID
) -> SimplifiedChatResponse:
    """
    Convert OpenAI response to simplified format.
    
    Args:
        openai_response: OpenAI chat response
        session_id: Session ID
        
    Returns:
        Simplified chat response
    """
    # Extract response data
    choice = openai_response.choices[0]
    message = choice.message
    
    # Extract metadata
    metadata = message.metadata or {}
    
    return SimplifiedChatResponse(
        session_id=session_id,
        message=message.content or "",
        risk_assessment=metadata.get("risk_assessment", "LOW"),
        should_see_doctor=metadata.get("should_see_doctor", False),
        tools_used=metadata.get("tools_used", []),
        disclaimer=metadata.get("disclaimer", ""),
        thinking_summary=metadata.get("thinking_summary")
    )


async def process_simplified_chat_request(
    db: Session,
    request: SimplifiedChatRequest,
    session_id: Optional[UUID] = None
) -> SimplifiedChatResponse:
    """
    Process simplified chat request (non-streaming).
    
    Args:
        db: Database session
        request: Simplified chat request
        session_id: Optional session ID from query parameter
        
    Returns:
        Simplified chat response
    """
    try:
        logger.info("Processing simplified chat request (non-streaming)")
        
        # Convert to OpenAI format
        openai_request = convert_simplified_to_openai_format(request, session_id)
        
        # Process with OpenAI service
        openai_response = await process_openai_chat_request(db, openai_request)
        
        # Extract session_id from response
        response_session_id = openai_response.session_id
        if response_session_id:
            # Parse string to UUID if needed
            if isinstance(response_session_id, str):
                from uuid import UUID as UUID_Type
                response_session_id = UUID_Type(response_session_id)
        else:
            # Fallback to input session_id or generate new one
            response_session_id = session_id or UUID("00000000-0000-0000-0000-000000000000")
        
        # Convert to simplified format
        simplified_response = convert_openai_to_simplified_response(
            openai_response,
            response_session_id
        )
        
        return simplified_response
        
    except Exception as e:
        logger.error(f"Error processing simplified chat request: {str(e)}")
        raise


async def process_simplified_chat_streaming(
    db: Session,
    request: SimplifiedChatRequest,
    session_id: Optional[UUID] = None
) -> AsyncGenerator[str, None]:
    """
    Process simplified chat request with streaming.
    
    Args:
        db: Database session
        request: Simplified chat request
        session_id: Optional session ID from query parameter
        
    Yields:
        SSE-formatted strings with simplified events
    """
    try:
        logger.info("Processing simplified chat request (streaming)")
        
        # Convert to OpenAI format
        openai_request = convert_simplified_to_openai_format(request, session_id)
        
        # Track accumulated data for final event
        accumulated_content = ""
        tools_used = []
        risk_assessment = "LOW"
        should_see_doctor = False
        disclaimer = ""
        thinking_steps = []
        final_session_id = None
        
        # Stream from OpenAI service
        async for sse_line in process_openai_chat_request_streaming(db, openai_request):
            # Parse OpenAI SSE format
            if sse_line.startswith("data: "):
                data_str = sse_line[6:].strip()
                
                if data_str == "[DONE]":
                    # Send final completion event with metadata
                    completion_event = SimplifiedStreamEvent(
                        type="complete",
                        data={
                            "session_id": str(final_session_id) if final_session_id else None,
                            "risk_assessment": risk_assessment,
                            "should_see_doctor": should_see_doctor,
                            "tools_used": tools_used,
                            "disclaimer": disclaimer,
                            "thinking_summary": " → ".join(thinking_steps[:3]) if thinking_steps else None
                        },
                        timestamp=datetime.utcnow().isoformat()
                    )
                    yield f"data: {completion_event.model_dump_json()}\n\n"
                    
                    # Send [DONE] marker
                    yield "data: [DONE]\n\n"
                    break
                
                try:
                    chunk = json.loads(data_str)
                    
                    # Extract event type
                    event_type = chunk.get("event_type")
                    event_data = chunk.get("event_data", {})
                    
                    if event_type == "thinking":
                        # Thinking event
                        thinking_text = event_data.get("thinking", "")
                        if thinking_text:
                            thinking_steps.append(thinking_text)
                        
                        thinking_event = SimplifiedStreamEvent(
                            type="thinking",
                            data=thinking_text,
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {thinking_event.model_dump_json()}\n\n"
                    
                    elif event_type == "tool_call":
                        # Tool call event
                        tool_event = SimplifiedStreamEvent(
                            type="tool",
                            data={
                                "tool_name": event_data.get("tool_name"),
                                "status": "calling"
                            },
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {tool_event.model_dump_json()}\n\n"
                    
                    elif event_type == "tool_result":
                        # Tool result event
                        tool_name = event_data.get("tool_name")
                        if tool_name and tool_name not in tools_used:
                            tools_used.append(tool_name)
                        
                        tool_event = SimplifiedStreamEvent(
                            type="tool",
                            data={
                                "tool_name": tool_name,
                                "status": "completed"
                            },
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {tool_event.model_dump_json()}\n\n"
                    
                    elif event_type == "done":
                        # Final event with metadata
                        if isinstance(event_data, dict):
                            final_session_id = event_data.get("session_id")
                            risk_assessment = event_data.get("risk_assessment", "LOW")
                            should_see_doctor = event_data.get("should_see_doctor", False)
                            disclaimer = event_data.get("disclaimer", "")
                            tools_used = event_data.get("tools_used", tools_used)
                    
                    elif event_type in ["vision_analysis", "vision_complete", "image_validation", "image_processing"]:
                        # Vision processing events - pass through as thinking
                        vision_event = SimplifiedStreamEvent(
                            type="thinking",
                            data=f"Processing image: {event_type}",
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {vision_event.model_dump_json()}\n\n"
                    
                    else:
                        # Content delta
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            
                            if content:
                                accumulated_content += content
                                
                                # Send content event
                                content_event = SimplifiedStreamEvent(
                                    type="content",
                                    data=content,
                                    timestamp=datetime.utcnow().isoformat()
                                )
                                yield f"data: {content_event.model_dump_json()}\n\n"
                
                except json.JSONDecodeError:
                    # Skip malformed chunks
                    pass
            
            # Pass through the line as-is for compatibility
            # (client can choose to parse simplified or raw format)
            
    except Exception as e:
        logger.error(f"Error in simplified streaming: {str(e)}")
        error_event = SimplifiedStreamEvent(
            type="error",
            data=f"Error: {str(e)}",
            timestamp=datetime.utcnow().isoformat()
        )
        yield f"data: {error_event.model_dump_json()}\n\n"

