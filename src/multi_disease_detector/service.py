"""
Service layer for Multi Disease Detector.
Handles LLM integration via OpenRouter API, context building, and session management.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Tuple, List
from uuid import UUID, uuid4

from sqlmodel import Session, select, func
from openai import OpenAI
from dotenv import load_dotenv

from .models import ChatSession, ChatMessage
from .schemas import ChatRequest, ChatResponse

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = "openai/gpt-oss-120b"  # Model available via OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MAX_HISTORY_MESSAGES = 10  # Limit context window
MAX_RESPONSE_TOKENS = 1024
DISCLAIMER_TEXT = (
    "⚠️ **Important Disclaimer**: This is an AI health assistant and should not replace "
    "professional medical advice, diagnosis, or treatment. Always consult with a qualified "
    "healthcare provider for proper medical guidance. If you're experiencing a medical emergency, "
    "call emergency services immediately."
)

# Initialize OpenAI Client for OpenRouter
_openai_client = None


def get_openai_client() -> OpenAI:
    """
    Get or initialize the OpenAI client configured for OpenRouter.
    
    Returns:
        OpenAI client instance
    """
    global _openai_client
    
    if _openai_client is None:
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found in environment variables")
            raise ValueError("OPENROUTER_API_KEY is required. Please set it in your .env file")
        
        # Initialize OpenAI client with OpenRouter endpoint
        _openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        logger.info(f"Initialized OpenAI client for OpenRouter with model: {MODEL_NAME}")
        logger.info("Using OpenRouter API: https://openrouter.ai/api/v1")
    
    return _openai_client


async def get_or_create_session(
    db: Session,
    session_id: Optional[UUID],
    patient_id: Optional[UUID],
    first_message: str
) -> ChatSession:
    """
    Get an existing session or create a new one.
    
    Args:
        db: Database session
        session_id: Optional existing session ID
        patient_id: Patient ID for new sessions
        first_message: First message to generate title from
        
    Returns:
        ChatSession instance
    """
    if session_id:
        # Retrieve existing session
        statement = select(ChatSession).where(ChatSession.id == session_id)
        session = db.exec(statement).first()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update last_message_at
        session.updated_at = datetime.utcnow()
        session.last_message_at = datetime.utcnow()
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    else:
        # Create new session
        if not patient_id:
            raise ValueError("patient_id is required for new sessions")
        
        # Generate title from first message (truncate if too long)
        title = first_message[:100] + "..." if len(first_message) > 100 else first_message
        
        new_session = ChatSession(
            patient_id=patient_id,
            title=title,
            status="ACTIVE",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_message_at=datetime.utcnow()
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f"Created new session: {new_session.id}")
        return new_session


def build_context_from_data(request: ChatRequest) -> str:
    """
    Build patient context string from optional input data.
    
    Args:
        request: ChatRequest with optional patient data
        
    Returns:
        Formatted context string
    """
    context_parts = []
    
    # Add consultation data
    if request.consultation_data:
        cd = request.consultation_data
        consultation_info = []
        if cd.chief_complaint:
            consultation_info.append(f"Chief Complaint: {cd.chief_complaint}")
        if cd.history_of_present_illness:
            consultation_info.append(f"History: {cd.history_of_present_illness}")
        if cd.assessment:
            consultation_info.append(f"Assessment: {cd.assessment}")
        if cd.treatment_plan:
            consultation_info.append(f"Treatment Plan: {cd.treatment_plan}")
        if cd.doctor_notes:
            consultation_info.append(f"Doctor Notes: {cd.doctor_notes}")
        
        if consultation_info:
            context_parts.append("=== Recent Consultation ===\n" + "\n".join(consultation_info))
    
    # Add vitals data
    if request.vitals_data:
        vd = request.vitals_data
        vitals_info = []
        if vd.blood_type:
            vitals_info.append(f"Blood Type: {vd.blood_type}")
        if vd.blood_pressure_systolic and vd.blood_pressure_diastolic:
            vitals_info.append(f"Blood Pressure: {vd.blood_pressure_systolic}/{vd.blood_pressure_diastolic} mmHg")
        if vd.heart_rate_bpm:
            vitals_info.append(f"Heart Rate: {vd.heart_rate_bpm} bpm")
        if vd.temperature_celsius:
            vitals_info.append(f"Temperature: {vd.temperature_celsius}°C")
        if vd.respiratory_rate:
            vitals_info.append(f"Respiratory Rate: {vd.respiratory_rate} breaths/min")
        if vd.oxygen_saturation:
            vitals_info.append(f"Oxygen Saturation: {vd.oxygen_saturation}%")
        if vd.glucose_level:
            vitals_info.append(f"Glucose Level: {vd.glucose_level} mg/dL")
        if vd.weight_kg:
            vitals_info.append(f"Weight: {vd.weight_kg} kg")
        if vd.height_cm:
            vitals_info.append(f"Height: {vd.height_cm} cm")
        if vd.bmi:
            vitals_info.append(f"BMI: {vd.bmi}")
        
        if vitals_info:
            context_parts.append("=== Vital Signs ===\n" + "\n".join(vitals_info))
    
    # Add habits data
    if request.habits_data and request.habits_data.habits:
        habits_info = []
        for habit in request.habits_data.habits:
            habit_str = f"- {habit.habit_type}"
            if habit.actual_value and habit.target_value:
                habit_str += f": {habit.actual_value}/{habit.target_value} {habit.target_unit or ''}"
            elif habit.actual_value:
                habit_str += f": {habit.actual_value} {habit.target_unit or ''}"
            if habit.notes:
                habit_str += f" ({habit.notes})"
            habits_info.append(habit_str)
        
        if habits_info:
            context_parts.append("=== Patient Habits ===\n" + "\n".join(habits_info))
    
    # Add conditions data
    if request.conditions_data and request.conditions_data.conditions:
        conditions_info = []
        for condition in request.conditions_data.conditions:
            cond_str = f"- {condition.condition_name}"
            if condition.status:
                cond_str += f" (Status: {condition.status}"
                if condition.severity:
                    cond_str += f", Severity: {condition.severity}"
                cond_str += ")"
            if condition.notes:
                cond_str += f"\n  Notes: {condition.notes}"
            conditions_info.append(cond_str)
        
        if conditions_info:
            context_parts.append("=== Medical Conditions ===\n" + "\n".join(conditions_info))
    
    # Add AI consultation data
    if request.ai_consultation_data:
        acd = request.ai_consultation_data
        ai_info = []
        if acd.symptoms_described:
            ai_info.append(f"Previous Symptoms: {acd.symptoms_described}")
        if acd.ai_suggested_conditions:
            ai_info.append(f"Suggested Conditions: {json.dumps(acd.ai_suggested_conditions)}")
        if acd.ai_recommendations:
            ai_info.append(f"Previous Recommendations: {acd.ai_recommendations}")
        if acd.risk_assessment:
            ai_info.append(f"Risk Assessment: {acd.risk_assessment}")
        
        if ai_info:
            context_parts.append("=== Previous AI Consultation ===\n" + "\n".join(ai_info))
    
    return "\n\n".join(context_parts) if context_parts else ""


async def get_session_history(db: Session, session_id: UUID, limit: int = MAX_HISTORY_MESSAGES) -> List[ChatMessage]:
    """
    Retrieve recent conversation history for a session.
    
    Args:
        db: Database session
        session_id: Session ID
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of ChatMessage instances
    """
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = db.exec(statement).all()
    return list(reversed(messages))  # Return in chronological order


def build_chat_messages(
    user_message: str,
    patient_context: str,
    conversation_history: List[ChatMessage]
) -> List[dict]:
    """
    Build chat messages in standard OpenAI format.
    
    Args:
        user_message: Current user message
        patient_context: Formatted patient context
        conversation_history: Previous messages in the conversation
        
    Returns:
        List of message dicts in OpenAI format
    """
    messages = []
    
    # System message with instructions
    system_content = (
        "You are an AI health consultant assisting patients with health-related questions. "
        "You provide helpful, empathetic, and medically-informed responses. "
        "Always remind users that you are an AI assistant and they should consult healthcare professionals for proper diagnosis and treatment. "
        "Be conversational and supportive while maintaining medical accuracy."
    )
    
    # Add patient context to system message if available
    if patient_context:
        system_content += f"\n\nPatient Context:\n{patient_context}"
    
    messages.append({
        "role": "system",
        "content": system_content
    })
    
    # Add conversation history
    for msg in conversation_history:
        messages.append({
            "role": "user" if msg.role == "USER" else "assistant",
            "content": msg.content
        })
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages


async def generate_response(messages: List[dict]) -> str:
    """
    Generate response from the LLM via OpenRouter API.
    
    Args:
        messages: List of message dicts in OpenAI format
        
    Returns:
        Generated response text
    """
    try:
        client = get_openai_client()
        
        # Call OpenRouter API with chat completion
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_RESPONSE_TOKENS,
            temperature=0.7,
            top_p=0.9,
        )
        
        # Extract the assistant's response
        assistant_message = completion.choices[0].message.content
        
        return assistant_message.strip()
        
    except Exception as e:
        logger.error(f"Error generating response from OpenRouter API: {str(e)}")
        return "I apologize, but I encountered an error while processing your request. Please try again later."


def calculate_risk_assessment(message: str, patient_context: str) -> Tuple[str, bool]:
    """
    Calculate risk assessment based on the conversation and context.
    
    Args:
        message: AI response message
        patient_context: Patient context data
        
    Returns:
        Tuple of (risk_level, should_see_doctor)
    """
    # Simple keyword-based risk assessment
    # In production, this could use a more sophisticated ML model
    
    emergency_keywords = [
        "chest pain", "severe pain", "difficulty breathing", "unconscious",
        "bleeding heavily", "stroke", "heart attack", "emergency", "911"
    ]
    
    high_risk_keywords = [
        "blood pressure", "diabetes", "chronic", "severe", "urgent",
        "worsening", "persistent", "infection", "high fever"
    ]
    
    medium_risk_keywords = [
        "pain", "discomfort", "symptoms", "condition", "medication",
        "treatment", "concern", "monitor"
    ]
    
    combined_text = (message + " " + patient_context).lower()
    
    # Check for emergency
    if any(keyword in combined_text for keyword in emergency_keywords):
        return "EMERGENCY", True
    
    # Check for high risk
    if any(keyword in combined_text for keyword in high_risk_keywords):
        return "HIGH", True
    
    # Check for medium risk
    if any(keyword in combined_text for keyword in medium_risk_keywords):
        return "MEDIUM", True
    
    # Default to low risk
    return "LOW", False


async def save_chat_exchange(
    db: Session,
    session_id: UUID,
    user_message: str,
    assistant_message: str,
    risk_assessment: str
) -> None:
    """
    Save user and assistant messages to the database.
    
    Args:
        db: Database session
        session_id: Session ID
        user_message: User's message
        assistant_message: AI's response
        risk_assessment: Calculated risk level
    """
    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="USER",
        content=user_message,
        created_at=datetime.utcnow()
    )
    db.add(user_msg)
    
    # Save assistant message with metadata
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="ASSISTANT",
        content=assistant_message,
        message_metadata={
            "risk_assessment": risk_assessment,
            "timestamp": datetime.utcnow().isoformat()
        },
        created_at=datetime.utcnow()
    )
    db.add(assistant_msg)
    
    db.commit()
    logger.info(f"Saved chat exchange for session {session_id}")


async def process_chat_request(db: Session, request: ChatRequest) -> ChatResponse:
    """
    Main function to process a chat request.
    
    Args:
        db: Database session
        request: Chat request data (session_id comes from query parameter)
        
    Returns:
        ChatResponse with AI-generated reply
    """
    try:
        # Step 1: Get or create session
        # session_id is injected from query parameter by the router
        session = await get_or_create_session(
            db=db,
            session_id=request.session_id,
            patient_id=request.patient_id,
            first_message=request.message
        )
        
        # Step 2: Build patient context from optional data
        patient_context = build_context_from_data(request)
        
        # Step 3: Get conversation history
        conversation_history = await get_session_history(db, session.id)
        
        # Step 4: Build chat messages in harmony format
        messages = build_chat_messages(
            user_message=request.message,
            patient_context=patient_context,
            conversation_history=conversation_history
        )
        
        # Step 5: Generate AI response via HuggingFace API
        ai_message = await generate_response(messages)
        
        # Step 6: Calculate risk assessment
        risk_level, should_see_doctor = calculate_risk_assessment(
            message=ai_message,
            patient_context=patient_context
        )
        
        # Step 7: Save chat exchange
        await save_chat_exchange(
            db=db,
            session_id=session.id,
            user_message=request.message,
            assistant_message=ai_message,
            risk_assessment=risk_level
        )
        
        # Step 8: Return response
        return ChatResponse(
            session_id=session.id,
            message=ai_message,
            risk_assessment=risk_level,
            should_see_doctor=should_see_doctor,
            disclaimer=DISCLAIMER_TEXT
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise

