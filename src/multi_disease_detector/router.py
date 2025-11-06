"""
FastAPI router for Multi Disease Detector endpoints.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
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
from .openai_schemas import OpenAIChatRequest, OpenAIChatResponse, ErrorResponse
from .openai_service import process_openai_chat_request, process_openai_chat_request_streaming
from .simplified_schemas import SimplifiedChatRequest, SimplifiedChatResponse
from .simplified_service import process_simplified_chat_request, process_simplified_chat_streaming
from .tools import get_tool_definitions

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/multi-disease-detector",
    tags=["Multi Disease Detector"],
    responses={404: {"description": "Not found"}}
)


# ===== PRIMARY UNIFIED ENDPOINT (SIMPLIFIED) =====

@router.post("/v1/chat")
async def unified_chat(
    request: SimplifiedChatRequest,
    session_id: Optional[UUID] = Query(None, description="Optional session ID for conversation continuity"),
    db: Session = Depends(get_db)
):
    """
    **⭐ PRIMARY Unified Chat Endpoint** 
    
    **This is the recommended endpoint for all client applications.**
    
    Simple, powerful API that consolidates all Multi Disease Detector functionality:
    - ✅ Conversational AI health consultation
    - ✅ Streaming responses (`stream: true`)
    - ✅ Medical image analysis
    - ✅ Automatic web search (Tavily)
    - ✅ Automatic document generation
    - ✅ Patient context integration
    - ✅ Session management
    
    ---
    
    ## Request Format
    
    **Simple JSON body** with `session_id` as query parameter:
    
    ```json
    POST /api/v1/multi-disease-detector/v1/chat?session_id=uuid-optional
    
    {
      "message": "What are the symptoms of type 2 diabetes?",
      "patient_id": "550e8400-e29b-41d4-a716-446655440000",
      "stream": false,
      "image": "base64-string-optional",
      "vitals_data": {
        "blood_pressure_systolic": 130,
        "blood_pressure_diastolic": 85,
        "heart_rate_bpm": 75
      },
      "consultation_data": {...},
      "habits_data": {...},
      "conditions_data": {...},
      "ai_consultation_data": {...}
    }
    ```
    
    ### Key Features
    
    - **No complex setup** - Just send your message and optional context
    - **session_id query parameter** - For conversation continuity
    - **Auto-configured** - Model, temperature, tokens managed internally
    - **Auto-tools** - Web search and document generation enabled automatically
    - **Simple responses** - Clean, focused response format
    
    ---
    
    ## Response Format
    
    ### Non-Streaming Response
    
    ```json
    {
      "session_id": "660e8400-e29b-41d4-a716-446655440001",
      "message": "Type 2 diabetes symptoms include increased thirst...",
      "risk_assessment": "MEDIUM",
      "should_see_doctor": true,
      "tools_used": ["tavily_web_search"],
      "disclaimer": "⚠️ Important medical disclaimer...",
      "thinking_summary": "Analyzed symptoms → Searched guidelines → Generated response"
    }
    ```
    
    ### Streaming Response (SSE)
    
    Set `"stream": true` in request body:
    
    ```
    data: {"type":"thinking","data":"Analyzing your question..."}
    
    data: {"type":"content","data":"Type 2"}
    
    data: {"type":"content","data":" diabetes"}
    
    data: {"type":"tool","data":{"tool_name":"tavily_web_search","status":"calling"}}
    
    data: {"type":"tool","data":{"tool_name":"tavily_web_search","status":"completed"}}
    
    data: {"type":"complete","data":{"session_id":"...","risk_assessment":"MEDIUM",...}}
    
    data: [DONE]
    ```
    
    ---
    
    ## Examples
    
    ### Example 1: Basic Chat
    
    ```bash
    curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/v1/chat" \\
      -H "Content-Type: application/json" \\
      -d '{
        "message": "What are the symptoms of type 2 diabetes?",
        "stream": false
      }'
    ```
    
    ### Example 2: Chat with Patient Context
    
    ```bash
    curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/v1/chat?session_id=my-session-uuid" \\
      -H "Content-Type: application/json" \\
      -d '{
        "message": "Should I be concerned about my blood pressure?",
        "patient_id": "550e8400-e29b-41d4-a716-446655440000",
        "vitals_data": {
          "blood_pressure_systolic": 145,
          "blood_pressure_diastolic": 95,
          "heart_rate_bpm": 82
        }
      }'
    ```
    
    ### Example 3: Chat with Image
    
    ```python
    import base64
    import requests
    
    # Read and encode image
    with open("medical_image.jpg", "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    response = requests.post(
        "http://localhost:8000/api/v1/multi-disease-detector/v1/chat",
        json={
            "message": "What is this rash?",
            "image": image_base64,
            "stream": False
        }
    )
    
    result = response.json()
    print(f"AI Response: {result['message']}")
    print(f"Risk: {result['risk_assessment']}")
    ```
    
    ### Example 4: Streaming Chat
    
    ```python
    import requests
    
    response = requests.post(
        "http://localhost:8000/api/v1/multi-disease-detector/v1/chat",
        json={
            "message": "Explain the treatment options for hypertension",
            "stream": True
        },
        stream=True
    )
    
    # Process SSE stream
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = line_str[6:]
                if data != '[DONE]':
                    import json
                    event = json.loads(data)
                    if event['type'] == 'content':
                        print(event['data'], end='', flush=True)
    ```
    
    ### Example 5: Continue Conversation
    
    ```python
    import requests
    
    # First message
    response1 = requests.post(
        "http://localhost:8000/api/v1/multi-disease-detector/v1/chat",
        json={
            "message": "What is diabetes?",
            "patient_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    )
    result1 = response1.json()
    session_id = result1['session_id']
    
    # Follow-up message (uses context from first message)
    response2 = requests.post(
        f"http://localhost:8000/api/v1/multi-disease-detector/v1/chat?session_id={session_id}",
        json={
            "message": "What are the treatment options?",
            "patient_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    )
    result2 = response2.json()
    print(result2['message'])
    ```
    
    ---
    
    ## Request Fields
    
    ### Required
    - **message** (string): User's question or message
    
    ### Optional
    - **patient_id** (UUID): Patient identifier for tracking
    - **session_id** (UUID, query param): For conversation continuity
    - **stream** (boolean): Enable streaming responses (default: false)
    - **image** (string): Base64-encoded image (JPEG, PNG, WEBP)
    
    ### Optional Patient Context
    - **consultation_data** (object): Recent consultation information
    - **vitals_data** (object): Latest vital signs
    - **habits_data** (object): Patient habits tracking
    - **conditions_data** (object): Active medical conditions
    - **ai_consultation_data** (object): Previous AI consultation data
    
    ---
    
    ## Response Fields
    
    - **session_id** (UUID): Session ID for conversation continuity
    - **message** (string): AI-generated response
    - **risk_assessment** (string): Risk level (LOW, MEDIUM, HIGH, EMERGENCY)
    - **should_see_doctor** (boolean): Whether to consult a doctor
    - **tools_used** (array): Tools used (e.g., ["tavily_web_search"])
    - **disclaimer** (string): Medical disclaimer
    - **thinking_summary** (string): Summary of AI's reasoning (optional)
    
    ---
    
    ## Event Types (Streaming)
    
    - **thinking**: AI reasoning process
    - **content**: Response content chunks
    - **tool**: Tool usage updates (calling/completed)
    - **complete**: Final event with metadata
    - **error**: Error occurred
    
    ---
    
    ## Automatic Features
    
    The following are handled automatically (no configuration needed):
    
    ✅ **Web Search**: AI automatically searches for current medical info when needed  
    ✅ **Document Generation**: Creates lab explanations, imaging analyses, summaries  
    ✅ **Image Analysis**: Processes medical images with vision AI  
    ✅ **Risk Assessment**: Evaluates medical risk level  
    ✅ **Session Management**: Tracks conversation history  
    ✅ **Model Configuration**: Optimized temperature, tokens, etc.  
    
    ---
    
    ## Migration from Legacy Endpoints
    
    | Legacy Endpoint | New Unified Endpoint |
    |----------------|---------------------|
    | `/chat` | `/v1/chat` |
    | `/chat/with-tools` | `/v1/chat` (tools auto-enabled) |
    | `/chat/stream` | `/v1/chat` with `stream: true` |
    
    **Changes needed:**
    - Move `session_id` from body to query parameter
    - Set `stream: true/false` in body instead of different endpoints
    - Everything else stays the same!
    
    ---
    
    ## Error Responses
    
    Errors return standard HTTP status codes with detail:
    
    ```json
    {
      "detail": "Error message here"
    }
    ```
    
    Common errors:
    - **400**: Invalid request (missing required fields, invalid data)
    - **500**: Server error (processing failed)
    
    ---
    
    ## Notes
    
    - **Recommended for all new integrations** - Simple, powerful, complete
    - **No setup required** - Just message + optional context
    - **Conversation continuity** - Use `session_id` query parameter
    - **Anonymous usage** - Works without `patient_id` (but recommended for tracking)
    - **Image format** - Send base64 string (with or without data URI prefix)
    - **Auto-tools** - Web search and documents enabled automatically
    - **Legacy compatible** - Old endpoints still work for backward compatibility
    
    ---
    
    ## Advanced Usage
    
    For advanced use cases requiring full OpenAI compatibility (e.g., custom models, explicit tool control), 
    see `/v1/chat/completions` endpoint.
    """
    try:
        # Handle streaming vs non-streaming
        if request.stream:
            logger.info("Processing simplified streaming request")
            return StreamingResponse(
                process_simplified_chat_streaming(db, request, session_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            logger.info("Processing simplified non-streaming request")
            response = await process_simplified_chat_request(db, request, session_id)
            return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in unified chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )


# ===== ADVANCED OPENAI-COMPLIANT ENDPOINT =====

@router.post("/v1/chat/completions", status_code=status.HTTP_200_OK)
async def openai_chat_completions(
    request: OpenAIChatRequest,
    db: Session = Depends(get_db)
):
    """
    **OpenAI-Compliant Chat Completions Endpoint** 
    
    This is the unified endpoint that consolidates all Multi Disease Detector functionality:
    - Basic conversational AI health consultation
    - Medical image analysis (vision)
    - Web search with Tavily for current medical information
    - Document generation (lab explanations, imaging analysis, medical summaries)
    - Streaming responses (Server-Sent Events)
    - Patient context integration
    - Session management for conversation continuity
    
    ---
    
    ## API Format
    
    Follows OpenAI Chat Completions API standard with custom extensions for medical use cases.
    
    ### Request Body
    
    ```json
    {
      "messages": [
        {"role": "system", "content": "You are a helpful medical AI assistant."},
        {"role": "user", "content": "What are the symptoms of diabetes?"}
      ],
      "model": "openai/gpt-oss-120b",
      "stream": false,
      "temperature": 0.7,
      "max_tokens": 1024,
      "tools": [...],  // Optional: Enable tool calling
      "patient_context": {  // Optional: HUE AI custom extension
        "patient_id": "uuid",
        "session_id": "uuid",
        "vitals_data": {...},
        "consultation_data": {...}
      }
    }
    ```
    
    ### Image Support
    
    Include images as base64-encoded data URIs in message content:
    
    ```json
    {
      "messages": [
        {
          "role": "user",
          "content": [
            {"type": "text", "text": "What is this rash?"},
            {
              "type": "image_url",
              "image_url": {
                "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
              }
            }
          ]
        }
      ]
    }
    ```
    
    ### Tool Calling
    
    Enable tools by including them in the request:
    
    ```json
    {
      "messages": [...],
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "tavily_web_search",
            "description": "Search the web for current medical information",
            "parameters": {...}
          }
        }
      ]
    }
    ```
    
    To use all available tools, fetch them from `/tools` endpoint or use the pre-defined set.
    
    ### Streaming
    
    Set `"stream": true` to receive Server-Sent Events:
    
    ```json
    {
      "messages": [...],
      "stream": true
    }
    ```
    
    Streaming response format (SSE):
    ```
    data: {"id":"chatcmpl-123","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"}}]}
    
    data: {"id":"chatcmpl-123","object":"chat.completion.chunk","choices":[{"delta":{"content":" world"}}]}
    
    data: [DONE]
    ```
    
    ### Patient Context (Custom Extension)
    
    HUE AI extends OpenAI format with medical context:
    
    ```json
    {
      "patient_context": {
        "patient_id": "550e8400-e29b-41d4-a716-446655440000",
        "session_id": "660e8400-e29b-41d4-a716-446655440001",
        "vitals_data": {
          "blood_pressure_systolic": 130,
          "blood_pressure_diastolic": 85,
          "heart_rate_bpm": 75,
          "temperature_celsius": 37.2
        },
        "consultation_data": {
          "chief_complaint": "Persistent headaches",
          "history_of_present_illness": "Daily headaches for 2 weeks"
        },
        "conditions_data": {
          "conditions": [
            {
              "condition_name": "Hypertension",
              "status": "ACTIVE",
              "severity": "MILD"
            }
          ]
        }
      }
    }
    ```
    
    ---
    
    ## Response Format
    
    ### Non-Streaming Response
    
    ```json
    {
      "id": "chatcmpl-abc123",
      "object": "chat.completion",
      "created": 1699999999,
      "model": "openai/gpt-oss-120b",
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "Type 2 diabetes symptoms include...",
            "metadata": {
              "risk_assessment": "MEDIUM",
              "should_see_doctor": true,
              "tools_used": ["tavily_web_search"],
              "disclaimer": "..."
            }
          },
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 100,
        "total_tokens": 150
      },
      "session_id": "660e8400-e29b-41d4-a716-446655440001"
    }
    ```
    
    ### Metadata Fields (Custom Extension)
    
    The response message includes medical metadata:
    - `risk_assessment`: Risk level (LOW, MEDIUM, HIGH, EMERGENCY)
    - `should_see_doctor`: Boolean recommendation
    - `tools_used`: List of tools called during generation
    - `disclaimer`: Medical disclaimer text
    
    ---
    
    ## Examples
    
    ### Example 1: Basic Chat
    
    ```bash
    curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/v1/chat/completions" \\
      -H "Content-Type: application/json" \\
      -d '{
        "messages": [
          {"role": "user", "content": "What are the symptoms of type 2 diabetes?"}
        ],
        "model": "openai/gpt-oss-120b"
      }'
    ```
    
    ### Example 2: Chat with Image
    
    ```python
    import base64
    import requests
    
    # Read and encode image
    with open("rash.jpg", "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    response = requests.post(
        "http://localhost:8000/api/v1/multi-disease-detector/v1/chat/completions",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is this rash?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "stream": False
        }
    )
    print(response.json())
    ```
    
    ### Example 3: Streaming with Tools
    
    ```python
    import requests
    
    response = requests.post(
        "http://localhost:8000/api/v1/multi-disease-detector/v1/chat/completions",
        json={
            "messages": [
                {"role": "user", "content": "What are the latest cholesterol treatment guidelines?"}
            ],
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "tavily_web_search",
                        "description": "Search the web for current medical information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]
        },
        stream=True
    )
    
    # Process SSE stream
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = line_str[6:]
                if data != '[DONE]':
                    print(data)
    ```
    
    ### Example 4: With Patient Context
    
    ```bash
    curl -X POST "http://localhost:8000/api/v1/multi-disease-detector/v1/chat/completions" \\
      -H "Content-Type: application/json" \\
      -d '{
        "messages": [
          {"role": "user", "content": "Should I be concerned about my blood pressure?"}
        ],
        "patient_context": {
          "patient_id": "550e8400-e29b-41d4-a716-446655440000",
          "vitals_data": {
            "blood_pressure_systolic": 145,
            "blood_pressure_diastolic": 95,
            "heart_rate_bpm": 82
          }
        }
      }'
    ```
    
    ---
    
    ## Comparison with Legacy Endpoints
    
    | Feature | `/v1/chat/completions` | Legacy `/chat`, `/chat/with-tools`, `/chat/stream` |
    |---------|------------------------|-----------------------------------------------------|
    | Format | OpenAI JSON | Multipart form-data |
    | Images | Base64 in messages | File upload |
    | Streaming | `stream: true` | Separate endpoint |
    | Tools | In request | Separate endpoint |
    | Standard | OpenAI compliant | Custom |
    | Recommended | ✅ Yes (new integrations) | Use for backward compatibility |
    
    ---
    
    ## Notes
    
    - This endpoint is **OpenAI API compliant** and can be used as a drop-in replacement for OpenAI's Chat Completions API
    - The `patient_context` field is a **custom extension** specific to HUE AI
    - Custom event types in streaming (like `vision_analysis`, `thinking`) are **non-standard extensions**
    - Legacy endpoints (`/chat`, `/chat/with-tools`, `/chat/stream`) remain available for backward compatibility
    - For session continuity, include `session_id` in `patient_context` or the system will create a new session
    - All available tools can be fetched from the tools definitions in the codebase
    
    ---
    
    ## Error Responses
    
    Errors follow OpenAI format:
    
    ```json
    {
      "error": {
        "message": "Invalid request: messages array is required",
        "type": "invalid_request_error",
        "param": "messages",
        "code": "missing_required_parameter"
      }
    }
    ```
    """
    try:
        # Auto-populate tools if not provided and tool_choice is auto
        if request.tools is None and request.tool_choice == "auto":
            # Use all available tools by default
            from .tools import TOOL_DEFINITIONS
            request.tools = [
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
            logger.info(f"Auto-populated {len(request.tools)} tools for request")
        
        # Handle streaming vs non-streaming
        if request.stream:
            logger.info("Processing streaming request")
            return StreamingResponse(
                process_openai_chat_request_streaming(db, request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            logger.info("Processing non-streaming request")
            response = await process_openai_chat_request(db, request)
            return response
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "message": str(e),
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "validation_error"
                }
            }
        )
    except Exception as e:
        logger.error(f"Error in OpenAI chat completions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "message": "An error occurred while processing your request",
                    "type": "server_error",
                    "param": None,
                    "code": "internal_error"
                }
            }
        )


# ===== LEGACY ENDPOINTS (Backward Compatibility) =====

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

