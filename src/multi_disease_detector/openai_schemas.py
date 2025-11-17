from datetime import datetime
from typing import Optional, List, Any, Dict, Union, Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ===== MESSAGE CONTENT TYPES =====

class TextContent(BaseModel):
    """Text content in a message."""
    type: Literal["text"] = "text"
    text: str


class ImageUrl(BaseModel):
    """Image URL or base64 data."""
    url: str = Field(..., description="Image URL or data URI (data:image/jpeg;base64,...)")
    detail: Optional[Literal["auto", "low", "high"]] = "auto"


class ImageContent(BaseModel):
    """Image content in a message."""
    type: Literal["image_url"] = "image_url"
    image_url: ImageUrl


# Content can be a string or array of content parts
MessageContent = Union[str, List[Union[TextContent, ImageContent]]]


# ===== FUNCTION/TOOL CALLING =====

class FunctionCall(BaseModel):
    """Function call structure."""
    name: str = Field(..., description="Function name")
    arguments: str = Field(..., description="Function arguments as JSON string")


class ToolCall(BaseModel):
    """Tool call structure in OpenAI format."""
    id: str = Field(..., description="Tool call ID")
    type: Literal["function"] = "function"
    function: FunctionCall


class ToolMessage(BaseModel):
    """Tool response message."""
    role: Literal["tool"] = "tool"
    content: str = Field(..., description="Tool execution result")
    tool_call_id: str = Field(..., description="ID of the tool call this responds to")


# ===== CHAT MESSAGES =====

class ChatMessage(BaseModel):
    """
    Chat message in OpenAI format.
    Supports system, user, assistant, and tool roles.
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[MessageContent] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None  # For tool role messages

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "role": "user",
                    "content": "What are the symptoms of diabetes?"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is this rash?"},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
                    ]
                },
                {
                    "role": "assistant",
                    "content": "Let me search for the latest information.",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "tavily_web_search", "arguments": '{"query": "diabetes symptoms"}'}
                        }
                    ]
                }
            ]
        }
    )


# ===== PATIENT CONTEXT EXTENSION (Custom) =====

class PatientContext(BaseModel):
    """
    Custom extension for patient context data.
    This is a non-standard extension specific to HUE AI.
    """
    patient_id: Optional[UUID] = Field(None, description="Patient UUID")
    session_id: Optional[UUID] = Field(None, description="Chat session UUID for conversation continuity")
    consultation_data: Optional[Dict[str, Any]] = Field(None, description="Recent consultation information")
    vitals_data: Optional[Dict[str, Any]] = Field(None, description="Latest vital signs")
    habits_data: Optional[Dict[str, Any]] = Field(None, description="Patient habits tracking")
    conditions_data: Optional[Dict[str, Any]] = Field(None, description="Active medical conditions")
    ai_consultation_data: Optional[Dict[str, Any]] = Field(None, description="Previous AI consultation data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "660e8400-e29b-41d4-a716-446655440001",
                "vitals_data": {
                    "blood_pressure_systolic": 130,
                    "blood_pressure_diastolic": 85,
                    "heart_rate_bpm": 75
                }
            }
        }
    )


# ===== TOOL DEFINITIONS =====

class FunctionParameters(BaseModel):
    """Function parameters schema."""
    type: Literal["object"] = "object"
    properties: Dict[str, Any]
    required: Optional[List[str]] = None


class FunctionDefinition(BaseModel):
    """Function definition for tool calling."""
    name: str
    description: Optional[str] = None
    parameters: Optional[FunctionParameters] = None


class ToolDefinition(BaseModel):
    """Tool definition in OpenAI format."""
    type: Literal["function"] = "function"
    function: FunctionDefinition


# ===== REQUEST SCHEMA =====

class OpenAIChatRequest(BaseModel):
    """
    OpenAI-compliant chat completion request.
    Includes custom patient_context extension for medical use cases.
    """
    messages: List[ChatMessage] = Field(..., description="Array of conversation messages")
    model: Optional[str] = Field(
        "openai/gpt-oss-120b",
        description="Model to use for generation. Default: openai/gpt-oss-120b"
    )
    
    # Generation parameters
    max_tokens: Optional[int] = Field(1024, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    stream: Optional[bool] = Field(False, description="Enable streaming responses (SSE)")
    
    # Tool calling
    tools: Optional[List[ToolDefinition]] = Field(None, description="Available tools for the model to call")
    tool_choice: Optional[Union[Literal["none", "auto"], Dict[str, Any]]] = Field(
        "auto",
        description="Controls tool calling behavior"
    )
    
    # Custom extensions (non-standard)
    patient_context: Optional[PatientContext] = Field(
        None,
        description="HUE AI custom extension: Patient medical context for enhanced responses"
    )
    
    # Other standard OpenAI parameters
    n: Optional[int] = Field(1, description="Number of completions to generate")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    presence_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0)
    user: Optional[str] = Field(None, description="Unique user identifier")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {"role": "system", "content": "You are a helpful medical AI assistant."},
                    {"role": "user", "content": "What are the symptoms of type 2 diabetes?"}
                ],
                "model": "openai/gpt-oss-120b",
                "temperature": 0.7,
                "max_tokens": 1024,
                "stream": False,
                "patient_context": {
                    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                    "vitals_data": {
                        "blood_pressure_systolic": 130,
                        "heart_rate_bpm": 75
                    }
                }
            }
        }
    )


# ===== RESPONSE SCHEMAS (Non-Streaming) =====

class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ResponseMessage(BaseModel):
    """Assistant message in response."""
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    
    # Custom extension: medical metadata
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="HUE AI extension: Additional metadata (risk assessment, tools used, etc.)"
    )


class ChatChoice(BaseModel):
    """A completion choice."""
    index: int
    message: ResponseMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None


class OpenAIChatResponse(BaseModel):
    """
    OpenAI-compliant chat completion response (non-streaming).
    """
    id: str = Field(..., description="Unique completion ID")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used")
    choices: List[ChatChoice]
    usage: Optional[UsageInfo] = None
    
    # Custom extensions
    session_id: Optional[str] = Field(None, description="HUE AI extension: Session ID for conversation continuity")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "chatcmpl-abc123",
                "object": "chat.completion",
                "created": 1699999999,
                "model": "openai/gpt-oss-120b",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Type 2 diabetes symptoms include increased thirst, frequent urination...",
                            "metadata": {
                                "risk_assessment": "MEDIUM",
                                "should_see_doctor": True
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
        }
    )


# ===== STREAMING RESPONSE SCHEMAS =====

class StreamDelta(BaseModel):
    """Delta content in streaming response."""
    role: Optional[Literal["assistant"]] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Partial tool calls


class StreamChoice(BaseModel):
    """Streaming choice."""
    index: int
    delta: StreamDelta
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None


class OpenAIStreamChunk(BaseModel):
    """
    OpenAI-compliant streaming response chunk.
    Sent as SSE: data: {json}\n\n
    """
    id: str = Field(..., description="Unique completion ID (same across all chunks)")
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(..., description="Unix timestamp")
    model: str
    choices: List[StreamChoice]
    
    # Custom extension events (non-standard)
    event_type: Optional[str] = Field(
        None,
        description="HUE AI extension: Event type (thinking, tool_call, vision_analysis, etc.)"
    )
    event_data: Optional[Dict[str, Any]] = Field(
        None,
        description="HUE AI extension: Additional event data"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "chatcmpl-abc123",
                "object": "chat.completion.chunk",
                "created": 1699999999,
                "model": "openai/gpt-oss-120b",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Type 2"},
                        "finish_reason": None
                    }
                ]
            }
        }
    )


# ===== ERROR RESPONSE =====

class ErrorDetail(BaseModel):
    """Error detail."""
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """OpenAI-style error response."""
    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "message": "Invalid request: messages array is required",
                    "type": "invalid_request_error",
                    "param": "messages",
                    "code": "missing_required_parameter"
                }
            }
        }
    )

