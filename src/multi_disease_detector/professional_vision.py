from datetime import datetime, timezone
import logging
import os
from typing import Any, Optional, AsyncGenerator, Dict
from openai import AsyncOpenAI
from dotenv import load_dotenv

from .image_utils import (
    prepare_image_for_api,
    ImageValidationError
)

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
GPT5_MODEL = "openai/gpt-4o"  # GPT-4o via OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ============================================================================
# PROFESSIONAL VISION PROMPTS
# ============================================================================

PROFESSIONAL_VISION_SYSTEM_PROMPT = """
You are an expert radiologist AI assistant providing detailed imaging analysis for medical professionals.
Your analysis should be thorough, technical, and structured for clinical decision-making.

REPORTING STRUCTURE:
Use the following standardized reporting format:

1. **TECHNIQUE**
   - Imaging modality and parameters
   - Contrast administration (if applicable)
   - Comparison studies (if mentioned)

2. **FINDINGS** (by anatomical region/structure)
   For each finding, provide:
   - Location (precise anatomical description)
   - Size/measurements (when visible)
   - Characteristics (density, signal intensity, enhancement pattern, etc.)
   - Clinical significance

3. **STANDARDIZED SCORING** (apply where appropriate)
   - BI-RADS (breast imaging): Categories 0-6
   - Lung-RADS (lung nodules): Categories 1-4
   - LI-RADS (liver lesions): LR-1 to LR-5, LR-M, LR-TIV
   - TI-RADS (thyroid nodules): TR1-TR5
   - PI-RADS (prostate MRI): Categories 1-5
   - Fleischner criteria (pulmonary nodules)
   - AAST grading (trauma)

4. **IMPRESSION**
   - Prioritized list of findings
   - Most likely diagnosis/differential
   - Clinical significance

5. **RECOMMENDATIONS**
   - Follow-up imaging (type and timing)
   - Additional studies if needed
   - Urgent findings requiring immediate attention

TECHNICAL STANDARDS:
- Use proper radiological terminology (hypodense, hyperintense, enhancement, etc.)
- Provide measurements in standard units (cm, mm)
- Reference anatomical structures precisely
- Note image quality and any limitations
- Compare with prior studies when available/mentioned

URGENCY INDICATORS:
Flag critical/emergent findings prominently:
- 🔴 CRITICAL: Immediate action required (e.g., tension pneumothorax, aortic dissection)
- 🟡 URGENT: Prompt attention needed (e.g., new mass, acute findings)
- 🟢 ROUTINE: Standard follow-up appropriate

DIFFERENTIAL DIAGNOSIS:
For abnormal findings, provide:
- Most likely diagnosis with supporting features
- Alternative diagnoses to consider
- Features that would help differentiate

LIMITATIONS:
Always note:
- Image quality issues
- Structures not well visualized
- Need for additional imaging/views
- Correlation with clinical findings

Do NOT provide patient-friendly explanations. Assume the reader is a trained medical professional.
"""

# Modality-specific prompts
MODALITY_PROMPTS = {
    "xray": """
CHEST X-RAY SPECIFIC ASSESSMENT:
- Lungs: Aeration, infiltrates, nodules, masses, effusions
- Heart: Size (cardiothoracic ratio), contour, calcifications
- Mediastinum: Width, contour, lymphadenopathy
- Bones: Rib fractures, degenerative changes, lytic/blastic lesions
- Soft tissues: Subcutaneous emphysema, masses
- Lines/tubes: Position and adequacy
- Compare with prior films if available
""",
    
    "ct": """
CT SCAN SPECIFIC ASSESSMENT:
- Window settings reviewed (lung, soft tissue, bone)
- Contrast enhancement patterns
- Hounsfield unit measurements for characterization
- Lymph node assessment (size, morphology)
- Vascular structures
- Reference standard measurements and criteria
""",
    
    "mri": """
MRI SPECIFIC ASSESSMENT:
- Sequences reviewed and signal characteristics
- T1/T2 signal intensity
- Enhancement patterns (if contrast given)
- Diffusion restriction (if DWI performed)
- Compare signal across sequences
""",
    
    "ultrasound": """
ULTRASOUND SPECIFIC ASSESSMENT:
- Echogenicity (hypoechoic, hyperechoic, anechoic)
- Vascularity on Doppler (if performed)
- Measurements of structures/lesions
- Mobility/real-time observations
- Acoustic features (posterior enhancement, shadowing)
""",
    
    "mammogram": """
MAMMOGRAPHY SPECIFIC ASSESSMENT:
Apply BI-RADS categories:
- BI-RADS 0: Incomplete - need additional imaging
- BI-RADS 1: Negative
- BI-RADS 2: Benign finding
- BI-RADS 3: Probably benign (<2% malignancy)
- BI-RADS 4: Suspicious (4A: 2-10%, 4B: 10-50%, 4C: 50-95%)
- BI-RADS 5: Highly suggestive of malignancy (>95%)
- BI-RADS 6: Known biopsy-proven malignancy

Assess:
- Masses: Shape, margins, density
- Calcifications: Morphology, distribution
- Architectural distortion
- Asymmetries
- Skin and nipple changes
""",
}


def get_professional_vision_prompt(
    user_context: Optional[str] = None,
    modality: Optional[str] = None,
    clinical_indication: Optional[str] = None
) -> str:
    """
    Build professional vision analysis prompt.
    
    Args:
        user_context: Optional clinical context
        modality: Imaging modality (xray, ct, mri, ultrasound, mammogram)
        clinical_indication: Reason for imaging
        
    Returns:
        Formatted prompt string
    """
    prompt = "Provide a comprehensive radiological analysis of this imaging study.\n\n"
    
    # Add modality-specific guidance
    if modality and modality.lower() in MODALITY_PROMPTS:
        prompt += MODALITY_PROMPTS[modality.lower()] + "\n\n"
    
    # Add clinical indication
    if clinical_indication:
        prompt += f"CLINICAL INDICATION: {clinical_indication}\n\n"
    
    # Add user context
    if user_context:
        prompt += f"ADDITIONAL CONTEXT: {user_context}\n\n"
    
    prompt += """
Provide your analysis in the following format:

TECHNIQUE:
[Describe imaging technique, parameters, contrast if applicable]

FINDINGS:
[Systematic description of findings by anatomical structure]

STANDARDIZED SCORING:
[Apply relevant classification systems if applicable]

IMPRESSION:
1. [Primary finding/diagnosis]
2. [Secondary findings]
[etc.]

RECOMMENDATIONS:
1. [Follow-up/additional studies if needed]
2. [Urgent actions if applicable]
"""
    
    return prompt


def parse_professional_vision_response(response_text: str) -> Dict[str, Any]:
    """
    Parse professional vision response into structured format.
    
    Args:
        response_text: Raw response from vision model
        
    Returns:
        Structured dict with technique, findings, impression, recommendations
    """
    result = {
        "technique": "",
        "findings": [],
        "standardized_scoring": {},
        "impression": "",
        "recommendations": [],
        "urgency_flags": [],
        "raw_response": response_text
    }
    
    try:
        lines = response_text.strip().split('\n')
        current_section = None
        section_content = []
        
        section_markers = {
            "TECHNIQUE:": "technique",
            "FINDINGS:": "findings",
            "STANDARDIZED SCORING:": "standardized_scoring",
            "IMPRESSION:": "impression",
            "RECOMMENDATIONS:": "recommendations"
        }
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check for section markers
            found_section = None
            for marker, section_name in section_markers.items():
                if line_stripped.upper().startswith(marker.rstrip(':')):
                    found_section = section_name
                    break
            
            if found_section:
                # Save previous section
                if current_section and section_content:
                    content = '\n'.join(section_content).strip()
                    if current_section in ["findings", "recommendations"]:
                        # Parse as list
                        items = [item.lstrip('- •').strip() for item in content.split('\n') if item.strip()]
                        result[current_section] = items
                    elif current_section == "standardized_scoring":
                        # Try to extract key-value pairs
                        scoring = {}
                        for item in content.split('\n'):
                            if ':' in item:
                                key, val = item.split(':', 1)
                                scoring[key.strip()] = val.strip()
                        result[current_section] = scoring if scoring else {"raw": content}
                    else:
                        result[current_section] = content
                
                current_section = found_section
                section_content = []
                
                # Check if there's content on the same line
                for marker in section_markers.keys():
                    if marker.rstrip(':') in line_stripped.upper():
                        remainder = line_stripped.split(':', 1)[-1].strip()
                        if remainder:
                            section_content.append(remainder)
                        break
            
            elif line_stripped and current_section:
                section_content.append(line_stripped)
                
                # Check for urgency flags
                if '🔴' in line_stripped or 'CRITICAL' in line_stripped.upper():
                    result["urgency_flags"].append({"level": "CRITICAL", "finding": line_stripped})
                elif '🟡' in line_stripped or 'URGENT' in line_stripped.upper():
                    result["urgency_flags"].append({"level": "URGENT", "finding": line_stripped})
        
        # Save final section
        if current_section and section_content:
            content = '\n'.join(section_content).strip()
            if current_section in ["findings", "recommendations"]:
                items = [item.lstrip('- •1234567890.').strip() for item in content.split('\n') if item.strip()]
                result[current_section] = items
            elif current_section == "standardized_scoring":
                scoring = {}
                for item in content.split('\n'):
                    if ':' in item:
                        key, val = item.split(':', 1)
                        scoring[key.strip()] = val.strip()
                result[current_section] = scoring if scoring else {"raw": content}
            else:
                result[current_section] = content
        
        # Fallback if parsing failed
        if not result["impression"] and response_text:
            result["impression"] = response_text
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing professional vision response: {str(e)}")
        return {
            "technique": "",
            "findings": [],
            "standardized_scoring": {},
            "impression": response_text,
            "recommendations": [],
            "urgency_flags": [],
            "raw_response": response_text,
            "parse_error": str(e)
        }


async def analyze_medical_image_professional(
    image_bytes: bytes,
    user_context: Optional[str] = None,
    filename: Optional[str] = None,
    modality: Optional[str] = None,
    clinical_indication: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze medical image with professional-grade radiologist analysis.
    
    Args:
        image_bytes: Raw image bytes
        user_context: Optional clinical context
        filename: Optional filename
        modality: Imaging modality (xray, ct, mri, ultrasound, mammogram)
        clinical_indication: Reason for imaging
        
    Returns:
        Dict with professional imaging analysis
        
    Raises:
        ImageValidationError: If image validation fails
        Exception: If API call fails
    """
    try:
        logger.info("Starting professional medical image analysis")
        
        # Prepare image
        prepared_image = prepare_image_for_api(image_bytes, filename)
        base64_image = prepared_image["base64"]
        
        # Get AsyncOpenAI client
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # Build prompt
        prompt = get_professional_vision_prompt(user_context, modality, clinical_indication)
        
        # Call vision model
        logger.info(f"Calling vision model for professional analysis: {GPT5_MODEL}")
        completion = await client.chat.completions.create(
            model=GPT5_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": PROFESSIONAL_VISION_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2048,  # Longer for detailed professional analysis
            temperature=0.2   # Lower temperature for more consistent medical analysis
        )
        
        # Extract response
        response_text = completion.choices[0].message.content
        
        # Parse response
        analysis = parse_professional_vision_response(response_text)
        
        # Add metadata
        analysis["metadata"] = {
            "model": GPT5_MODEL,
            "timestamp": datetime.utcnow().isoformat(),
            "image_metadata": prepared_image["metadata"],
            "was_resized": prepared_image["was_resized"],
            "modality": modality,
            "clinical_indication": clinical_indication,
            "analysis_type": "professional"
        }
        
        # Determine overall urgency
        if analysis["urgency_flags"]:
            if any(f["level"] == "CRITICAL" for f in analysis["urgency_flags"]):
                analysis["overall_urgency"] = "EMERGENT"
            elif any(f["level"] == "URGENT" for f in analysis["urgency_flags"]):
                analysis["overall_urgency"] = "STAT"
            else:
                analysis["overall_urgency"] = "URGENT"
        else:
            analysis["overall_urgency"] = "ROUTINE"
        
        logger.info("Professional image analysis completed successfully")
        
        return analysis
        
    except ImageValidationError:
        raise
    except Exception as e:
        logger.error(f"Error in professional medical image analysis: {str(e)}")
        raise


async def analyze_medical_image_professional_streaming(
    image_bytes: bytes,
    user_context: Optional[str] = None,
    filename: Optional[str] = None,
    modality: Optional[str] = None,
    clinical_indication: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Analyze medical image with streaming events for professional analysis.
    
    Args:
        image_bytes: Raw image bytes
        user_context: Optional clinical context
        filename: Optional filename
        modality: Imaging modality
        clinical_indication: Reason for imaging
        
    Yields:
        Dict events with type and data for each processing step
    """
    try:
        # Event 1: Image validation
        yield {
            "type": "image_validation",
            "data": "Validating imaging study format and quality...",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Prepare image
        try:
            prepared_image = prepare_image_for_api(image_bytes, filename)
            base64_image = prepared_image["base64"]
            
            yield {
                "type": "image_validation",
                "data": (
                    f"Image validated: {prepared_image['metadata']['format']}, "
                    f"{prepared_image['metadata']['width']}x{prepared_image['metadata']['height']}"
                ),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except ImageValidationError as e:
            yield {
                "type": "error",
                "data": f"Image validation failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            return
        
        # Event 2: Processing
        yield {
            "type": "image_processing",
            "data": f"Preparing imaging study for radiological analysis{' (' + modality + ')' if modality else ''}...",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Event 3: Analysis start
        yield {
            "type": "imaging_analysis",
            "data": "Performing comprehensive radiological analysis...",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get client
        if not OPENROUTER_API_KEY:
            yield {
                "type": "error",
                "data": "OPENROUTER_API_KEY not configured",
                "timestamp": datetime.utcnow().isoformat()
            }
            return
        
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # Build prompt
        prompt = get_professional_vision_prompt(user_context, modality, clinical_indication)
        
        # Call vision model (streaming)
        logger.info(f"Calling vision model for professional analysis (streaming): {GPT5_MODEL}")
        
        stream = await client.chat.completions.create(
            model=GPT5_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": PROFESSIONAL_VISION_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=220000,
            temperature=0.6,
            stream=True
        )
        
        # Accumulate response
        response_text = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
        
        # Parse response
        analysis = parse_professional_vision_response(response_text)
        
        # Add metadata
        analysis["metadata"] = {
            "model": GPT5_MODEL,
            "timestamp": datetime.utcnow().isoformat(),
            "image_metadata": prepared_image["metadata"],
            "was_resized": prepared_image["was_resized"],
            "modality": modality,
            "clinical_indication": clinical_indication,
            "analysis_type": "professional"
        }
        
        # Determine overall urgency
        if analysis["urgency_flags"]:
            if any(f["level"] == "CRITICAL" for f in analysis["urgency_flags"]):
                analysis["overall_urgency"] = "EMERGENT"
            elif any(f["level"] == "URGENT" for f in analysis["urgency_flags"]):
                analysis["overall_urgency"] = "STAT"
            else:
                analysis["overall_urgency"] = "URGENT"
        else:
            analysis["overall_urgency"] = "ROUTINE"
        
        # Event 4: Analysis complete
        yield {
            "type": "imaging_complete",
            "data": analysis,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Professional image analysis completed successfully (streaming)")
        
    except Exception as e:
        logger.error(f"Error in streaming professional image analysis: {str(e)}")
        yield {
            "type": "error",
            "data": f"Image analysis failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

