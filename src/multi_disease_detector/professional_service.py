import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Any, AsyncGenerator
from uuid import UUID

from sqlmodel import Session

from .professional_schemas import (
    ProfessionalChatRequest,
    ProfessionalChatResponse,
    ProfessionalStreamEvent,
    ProfessionalRole,
    Urgency,
    ClinicalInsights,
    DifferentialDiagnosis,
    TreatmentConsideration,
    ClinicalLikelihood,
    ImagingFindings,
)
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

# Internal configuration
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 32768
DEFAULT_TOP_P = 0.9

# Clinical disclaimer (professional version - concise)
PROFESSIONAL_DISCLAIMER = (
    "Clinical decision support only. This AI analysis should be verified independently. "
    "Final clinical decisions and patient care responsibilities rest with the treating provider."
)

# ============================================================================
# PROFESSIONAL SYSTEM PROMPTS
# ============================================================================

PROFESSIONAL_SYSTEM_PROMPT_BASE = """
You are an expert AI clinical decision support system designed for healthcare professionals.
You provide evidence-based clinical analysis with appropriate medical terminology.

CORE PRINCIPLES:
1. Use precise medical terminology and standard abbreviations
2. Provide structured differential diagnoses ranked by likelihood
3. Reference current clinical guidelines (ACC/AHA, ACOG, NCCN, IDSA, etc.)
4. Include pertinent positives AND negatives in your analysis
5. Suggest appropriate diagnostic workup with rationale
6. Discuss treatment options with dosing, contraindications, and monitoring
7. Identify red flags and time-sensitive conditions
8. Note evidence levels when discussing recommendations (Class I/II/III, Level A/B/C)

RESPONSE STRUCTURE:
When analyzing clinical cases, structure your response as follows:

1. **Clinical Summary**: Brief synthesis of the presentation
2. **Differential Diagnosis**: Ranked list with likelihood and rationale
   - Include pertinent positives and negatives supporting each
3. **Recommended Workup**: Specific tests with clinical justification
4. **Treatment Considerations**: Evidence-based options with dosing
5. **Red Flags**: Time-sensitive findings requiring immediate action
6. **Clinical Pearls**: Teaching points and common pitfalls
7. **References**: Cite relevant guidelines

WHEN ANALYZING IMAGES:
- Use standardized reporting frameworks (BI-RADS, Lung-RADS, LI-RADS, TI-RADS, etc.)
- Describe findings systematically by anatomical structure
- Provide measurements when visible
- Note comparison with prior studies if mentioned
- Give clear impression and recommendations

COMMUNICATION STYLE:
- Be direct and concise - professionals don't need excessive qualifiers
- Use standard medical abbreviations (HTN, DM, CAD, PE, etc.)
- Focus on actionable clinical information
- Acknowledge uncertainty with probability language, not vague hedging
- Don't repeat the obvious - assume baseline medical knowledge

RISK STRATIFICATION:
Assess clinical risk as:
- LOW: Stable, can be managed outpatient, routine follow-up
- MODERATE: Requires close monitoring, consider admission, timely workup
- HIGH: Likely requires admission, urgent intervention needed
- CRITICAL: Life-threatening, immediate intervention required

URGENCY CLASSIFICATION:
- ROUTINE: Standard outpatient timeframe
- URGENT: Within 24-48 hours
- STAT: Within hours
- EMERGENT: Immediate action required
"""

# Role-specific prompt additions
ROLE_PROMPTS = {
    ProfessionalRole.PHYSICIAN: """
PHYSICIAN-SPECIFIC GUIDANCE:
- Provide comprehensive differential diagnoses
- Include specific treatment protocols with dosing
- Consider drug interactions and contraindications
- Suggest appropriate specialist consultations
- Address both immediate management and disposition
""",
    
    ProfessionalRole.RADIOLOGIST: """
RADIOLOGIST-SPECIFIC GUIDANCE:
- Use standardized reporting templates
- Apply appropriate classification systems (BI-RADS, Lung-RADS, LI-RADS, TI-RADS, PI-RADS, etc.)
- Describe findings systematically by structure/region
- Provide specific measurements when visible
- Compare with priors if mentioned
- Give clear impression with actionable recommendations
- Note technical quality/limitations
""",
    
    ProfessionalRole.NURSE: """
NURSE-SPECIFIC GUIDANCE:
- Focus on assessment findings and their significance
- Include nursing considerations for care planning
- Highlight monitoring parameters and frequency
- Note medication administration considerations
- Include patient safety concerns
- Address patient education points
- Consider documentation requirements
""",
    
    ProfessionalRole.PHARMACIST: """
PHARMACIST-SPECIFIC GUIDANCE:
- Focus on medication-related analysis
- Include drug-drug interactions
- Note renal/hepatic dosing adjustments
- Address therapeutic monitoring needs
- Consider formulary alternatives
- Include patient counseling points
- Note high-alert medication concerns
""",
    
    ProfessionalRole.SPECIALIST: """
SPECIALIST-SPECIFIC GUIDANCE:
- Provide in-depth analysis within specialty domain
- Reference specialty-specific guidelines
- Include advanced diagnostic considerations
- Discuss specialized treatment options
- Consider clinical trial eligibility if applicable
""",
    
    ProfessionalRole.RESIDENT: """
RESIDENT-SPECIFIC GUIDANCE:
- Include teaching points and clinical pearls
- Explain the reasoning behind recommendations
- Note common pitfalls and mistakes
- Reference key studies and guidelines with context
- Include "don't miss" diagnoses
- Provide systematic approach frameworks
""",
    
    ProfessionalRole.PA: """
PA-SPECIFIC GUIDANCE:
- Balance comprehensive assessment with efficiency
- Include when to escalate to supervising physician
- Focus on common presentations and red flags
- Provide clear disposition recommendations
""",
    
    ProfessionalRole.NP: """
NP-SPECIFIC GUIDANCE:
- Balance comprehensive assessment with efficiency
- Include when to refer to specialists
- Focus on primary care and common presentations
- Address health maintenance and prevention
""",
}


def get_professional_system_prompt(role: Optional[ProfessionalRole] = None) -> str:
    """
    Build the system prompt for professional consultation.
    
    Args:
        role: Optional professional role for role-specific guidance
        
    Returns:
        Complete system prompt string
    """
    prompt = PROFESSIONAL_SYSTEM_PROMPT_BASE
    
    if role and role in ROLE_PROMPTS:
        prompt += "\n\n" + ROLE_PROMPTS[role]
    elif role == ProfessionalRole.OTHER:
        prompt += "\n\nProvide expert clinical analysis appropriate for healthcare professionals."
    
    return prompt


def build_clinical_context_string(request: ProfessionalChatRequest) -> str:
    """
    Build formatted clinical context from request data.
    
    Args:
        request: Professional chat request with clinical data
        
    Returns:
        Formatted clinical context string
    """
    context_parts = []
    
    # Add clinical context if provided
    if request.clinical_context:
        cc = request.clinical_context
        clinical_info = []
        
        if cc.get('chief_complaint'):
            clinical_info.append(f"CC: {cc['chief_complaint']}")
        if cc.get('history_present_illness'):
            clinical_info.append(f"HPI: {cc['history_present_illness']}")
        if cc.get('past_medical_history'):
            pmh = cc['past_medical_history']
            if isinstance(pmh, list):
                clinical_info.append(f"PMH: {', '.join(pmh)}")
            else:
                clinical_info.append(f"PMH: {pmh}")
        if cc.get('medications'):
            meds = cc['medications']
            if isinstance(meds, list):
                clinical_info.append(f"Medications: {', '.join(meds)}")
            else:
                clinical_info.append(f"Medications: {meds}")
        if cc.get('allergies'):
            allergies = cc['allergies']
            if isinstance(allergies, list):
                clinical_info.append(f"Allergies: {', '.join(allergies)}")
            else:
                clinical_info.append(f"Allergies: {allergies}")
        if cc.get('vitals'):
            vitals = cc['vitals']
            vitals_str = ', '.join([f"{k}: {v}" for k, v in vitals.items()])
            clinical_info.append(f"Vitals: {vitals_str}")
        if cc.get('labs'):
            labs = cc['labs']
            labs_str = ', '.join([f"{k}: {v}" for k, v in labs.items()])
            clinical_info.append(f"Labs: {labs_str}")
        if cc.get('imaging'):
            clinical_info.append(f"Imaging: {cc['imaging']}")
        if cc.get('physical_exam'):
            clinical_info.append(f"PE: {cc['physical_exam']}")
        
        if clinical_info:
            context_parts.append("=== Clinical Context ===\n" + "\n".join(clinical_info))
    
    # Add vitals data (backward compatible with patient schema)
    if request.vitals_data:
        vd = request.vitals_data
        vitals_info = []
        
        if vd.get('blood_pressure_systolic') and vd.get('blood_pressure_diastolic'):
            vitals_info.append(f"BP: {vd['blood_pressure_systolic']}/{vd['blood_pressure_diastolic']}")
        if vd.get('heart_rate_bpm'):
            vitals_info.append(f"HR: {vd['heart_rate_bpm']}")
        if vd.get('respiratory_rate'):
            vitals_info.append(f"RR: {vd['respiratory_rate']}")
        if vd.get('temperature_celsius'):
            vitals_info.append(f"Temp: {vd['temperature_celsius']}°C")
        if vd.get('oxygen_saturation'):
            vitals_info.append(f"SpO2: {vd['oxygen_saturation']}%")
        if vd.get('glucose_level'):
            vitals_info.append(f"Glucose: {vd['glucose_level']} mg/dL")
        
        if vitals_info and not request.clinical_context:
            context_parts.append("=== Vitals ===\n" + ", ".join(vitals_info))
    
    # Add conditions data
    if request.conditions_data and request.conditions_data.get('conditions'):
        conditions_info = []
        for condition in request.conditions_data['conditions']:
            cond_str = condition.get('condition_name', 'Unknown')
            if condition.get('status'):
                cond_str += f" ({condition['status']})"
            conditions_info.append(cond_str)
        
        if conditions_info:
            context_parts.append("=== Active Conditions ===\n" + ", ".join(conditions_info))
    
    # Add consultation data
    if request.consultation_data:
        cd = request.consultation_data
        consult_info = []
        
        if cd.get('assessment'):
            consult_info.append(f"Assessment: {cd['assessment']}")
        if cd.get('treatment_plan'):
            consult_info.append(f"Plan: {cd['treatment_plan']}")
        if cd.get('doctor_notes'):
            consult_info.append(f"Notes: {cd['doctor_notes']}")
        
        if consult_info:
            context_parts.append("=== Prior Consultation ===\n" + "\n".join(consult_info))
    
    return "\n\n".join(context_parts) if context_parts else ""


def convert_professional_to_openai_format(
    request: ProfessionalChatRequest,
    session_id: Optional[UUID] = None
) -> OpenAIChatRequest:
    """
    Convert professional request to OpenAI format.
    
    Args:
        request: Professional chat request
        session_id: Optional session ID from query parameter
        
    Returns:
        OpenAI-compliant chat request
    """
    messages = []
    
    # Build system message with role-specific guidance
    system_prompt = get_professional_system_prompt(request.professional_role)
    
    # Add clinical context to system message
    clinical_context = build_clinical_context_string(request)
    if clinical_context:
        system_prompt += f"\n\n=== PATIENT DATA ===\n{clinical_context}"
    
    messages.append(ChatMessage(
        role="system",
        content=system_prompt
    ))
    
    # Build user message
    if request.image:
        # Message with image - use content array
        user_content = [
            TextContent(type="text", text=request.message)
        ]
        
        # Add image
        if request.image.startswith("data:image/"):
            image_url = request.image
        else:
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
        messages.append(ChatMessage(
            role="user",
            content=request.message
        ))
    
    # Build patient context for session tracking
    patient_context = None
    if request.patient_id or session_id:
        patient_context = PatientContext(
            patient_id=request.patient_id,
            session_id=session_id,
            consultation_data=request.consultation_data,
            vitals_data=request.vitals_data,
            habits_data=request.habits_data,
            conditions_data=request.conditions_data,
            ai_consultation_data=request.ai_consultation_data
        )
    
    # Build tools array
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
    
    return OpenAIChatRequest(
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


def extract_clinical_insights(message: str) -> Optional[ClinicalInsights]:
    """
    Extract structured clinical insights from the response message.
    
    This is a heuristic extraction - ideally the LLM would return structured data.
    
    Args:
        message: AI-generated response message
        
    Returns:
        ClinicalInsights if extractable, None otherwise
    """
    # For now, return None - structured extraction can be enhanced later
    # The AI response will contain this information in natural language
    # Future enhancement: Use a separate LLM call to structure the response
    return None


def extract_imaging_findings(message: str) -> Optional[ImagingFindings]:
    """
    Extract structured imaging findings from the response message.
    
    Args:
        message: AI-generated response message
        
    Returns:
        ImagingFindings if extractable, None otherwise
    """
    # For now, return None - structured extraction can be enhanced later
    return None


def determine_urgency(risk_level: str, message: str) -> Urgency:
    """
    Determine clinical urgency based on risk level and content.
    
    Args:
        risk_level: Risk stratification level
        message: Response content
        
    Returns:
        Urgency classification
    """
    # Check for emergency keywords
    emergency_keywords = [
        'stat', 'emergent', 'immediate', 'life-threatening', 
        'cardiac arrest', 'code', 'crash', 'airway', 'hemorrhage',
        'stemi', 'stroke', 'sepsis', 'shock'
    ]
    message_lower = message.lower()
    
    if risk_level == "CRITICAL" or any(kw in message_lower for kw in ['emergent', 'immediate', 'code']):
        return Urgency.EMERGENT
    elif risk_level == "HIGH" or any(kw in message_lower for kw in ['stat', 'urgent']):
        return Urgency.STAT
    elif risk_level == "MODERATE":
        return Urgency.URGENT
    else:
        return Urgency.ROUTINE


def convert_openai_to_professional_response(
    openai_response: Any,
    session_id: UUID
) -> ProfessionalChatResponse:
    """
    Convert OpenAI response to professional format.
    
    Args:
        openai_response: OpenAI chat response
        session_id: Session ID
        
    Returns:
        Professional chat response
    """
    choice = openai_response.choices[0]
    message = choice.message
    metadata = message.metadata or {}
    
    # Get risk level from metadata or default
    risk_assessment = metadata.get("risk_assessment", "MODERATE")
    
    # Map patient-facing risk to professional risk stratification
    risk_mapping = {
        "LOW": "LOW",
        "MEDIUM": "MODERATE",
        "HIGH": "HIGH",
        "EMERGENCY": "CRITICAL"
    }
    risk_stratification = risk_mapping.get(risk_assessment, "MODERATE")
    
    # Determine urgency
    urgency = determine_urgency(risk_stratification, message.content or "")
    
    # Extract structured insights (if possible)
    clinical_insights = extract_clinical_insights(message.content or "")
    imaging_findings = extract_imaging_findings(message.content or "")
    
    # Extract references from message (simple heuristic)
    references = []
    content = message.content or ""
    if "guidelines" in content.lower() or "study" in content.lower():
        # TODO: Enhanced extraction of specific references
        pass
    
    return ProfessionalChatResponse(
        session_id=session_id,
        message=content,
        clinical_insights=clinical_insights,
        imaging_findings=imaging_findings,
        risk_stratification=risk_stratification,
        urgency=urgency,
        references=references,
        tools_used=metadata.get("tools_used", []),
        thinking_summary=metadata.get("thinking_summary"),
        clinical_caveat=PROFESSIONAL_DISCLAIMER
    )


async def process_professional_chat_request(
    db: Session,
    request: ProfessionalChatRequest,
    session_id: Optional[UUID] = None
) -> ProfessionalChatResponse:
    """
    Process professional chat request (non-streaming).
    
    Args:
        db: Database session
        request: Professional chat request
        session_id: Optional session ID from query parameter
        
    Returns:
        Professional chat response with clinical insights
    """
    try:
        logger.info(f"Processing professional chat request (role: {request.professional_role})")
        
        # Convert to OpenAI format with professional prompts
        openai_request = convert_professional_to_openai_format(request, session_id)
        
        # Process with OpenAI service
        openai_response = await process_openai_chat_request(db, openai_request)
        
        # Extract session_id from response
        response_session_id = openai_response.session_id
        if response_session_id:
            if isinstance(response_session_id, str):
                from uuid import UUID as UUID_Type
                response_session_id = UUID_Type(response_session_id)
        else:
            response_session_id = session_id or UUID("00000000-0000-0000-0000-000000000000")
        
        # Convert to professional format
        professional_response = convert_openai_to_professional_response(
            openai_response,
            response_session_id
        )
        
        return professional_response
        
    except Exception as e:
        logger.error(f"Error processing professional chat request: {str(e)}")
        raise


async def process_professional_chat_streaming(
    db: Session,
    request: ProfessionalChatRequest,
    session_id: Optional[UUID] = None
) -> AsyncGenerator[str, None]:
    """
    Process professional chat request with streaming.
    
    Args:
        db: Database session
        request: Professional chat request
        session_id: Optional session ID from query parameter
        
    Yields:
        SSE-formatted strings with professional events
    """
    try:
        logger.info(f"Processing professional chat request (streaming, role: {request.professional_role})")
        
        # Convert to OpenAI format with professional prompts
        openai_request = convert_professional_to_openai_format(request, session_id)
        
        # Track accumulated data
        accumulated_content = ""
        tools_used = []
        risk_assessment = "MODERATE"
        thinking_steps = []
        final_session_id = None
        
        # Stream from OpenAI service
        async for sse_line in process_openai_chat_request_streaming(db, openai_request):
            if sse_line.startswith("data: "):
                data_str = sse_line[6:].strip()
                
                if data_str == "[DONE]":
                    # Determine urgency
                    urgency = determine_urgency(risk_assessment, accumulated_content)
                    
                    # Send final completion event
                    completion_event = ProfessionalStreamEvent(
                        type="complete",
                        data={
                            "session_id": str(final_session_id) if final_session_id else None,
                            "risk_stratification": risk_assessment,
                            "urgency": urgency.value,
                            "tools_used": tools_used,
                            "clinical_caveat": PROFESSIONAL_DISCLAIMER,
                            "thinking_summary": " → ".join(thinking_steps[:3]) if thinking_steps else None
                        },
                        timestamp=datetime.utcnow().isoformat()
                    )
                    yield f"data: {completion_event.model_dump_json()}\n\n"
                    await asyncio.sleep(0)
                    
                    yield "data: [DONE]\n\n"
                    await asyncio.sleep(0)
                    break
                
                try:
                    chunk = json.loads(data_str)
                    event_type = chunk.get("event_type")
                    event_data = chunk.get("event_data", {})
                    
                    if event_type == "thinking":
                        thinking_text = event_data.get("thinking", "")
                        if thinking_text:
                            thinking_steps.append(thinking_text)
                        
                        # Convert to clinical_thinking event
                        thinking_event = ProfessionalStreamEvent(
                            type="clinical_thinking",
                            data=thinking_text,
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {thinking_event.model_dump_json()}\n\n"
                        await asyncio.sleep(0)
                    
                    elif event_type == "tool_call":
                        tool_event = ProfessionalStreamEvent(
                            type="tool",
                            data={
                                "tool_name": event_data.get("tool_name"),
                                "status": "calling"
                            },
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {tool_event.model_dump_json()}\n\n"
                        await asyncio.sleep(0)
                    
                    elif event_type == "tool_result":
                        tool_name = event_data.get("tool_name")
                        if tool_name and tool_name not in tools_used:
                            tools_used.append(tool_name)
                        
                        tool_event = ProfessionalStreamEvent(
                            type="tool",
                            data={
                                "tool_name": tool_name,
                                "status": "completed"
                            },
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {tool_event.model_dump_json()}\n\n"
                        await asyncio.sleep(0)
                    
                    elif event_type == "done":
                        if isinstance(event_data, dict):
                            final_session_id = event_data.get("session_id")
                            # Map risk assessment
                            raw_risk = event_data.get("risk_assessment", "MEDIUM")
                            risk_mapping = {"LOW": "LOW", "MEDIUM": "MODERATE", "HIGH": "HIGH", "EMERGENCY": "CRITICAL"}
                            risk_assessment = risk_mapping.get(raw_risk, "MODERATE")
                            tools_used = event_data.get("tools_used", tools_used)
                    
                    elif event_type in ["vision_analysis", "vision_complete"]:
                        # Imaging analysis events
                        imaging_event = ProfessionalStreamEvent(
                            type="imaging_analysis",
                            data=event_data if event_type == "vision_complete" else f"Analyzing imaging: {event_type}",
                            timestamp=datetime.utcnow().isoformat()
                        )
                        yield f"data: {imaging_event.model_dump_json()}\n\n"
                        await asyncio.sleep(0)
                    
                    else:
                        # Content delta
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            
                            if content:
                                accumulated_content += content
                                
                                content_event = ProfessionalStreamEvent(
                                    type="content",
                                    data=content,
                                    timestamp=datetime.utcnow().isoformat()
                                )
                                yield f"data: {content_event.model_dump_json()}\n\n"
                                await asyncio.sleep(0)
                
                except json.JSONDecodeError:
                    pass
    
    except Exception as e:
        logger.error(f"Error in professional streaming: {str(e)}")
        error_event = ProfessionalStreamEvent(
            type="error",
            data=f"Error: {str(e)}",
            timestamp=datetime.utcnow().isoformat()
        )
        yield f"data: {error_event.model_dump_json()}\n\n"
        await asyncio.sleep(0)

