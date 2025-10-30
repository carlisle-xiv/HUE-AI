"""
Vision service for Multi Disease Detector.
Integrates with GPT-5 via OpenRouter for medical image analysis.
GPT-5 acts as the "eyes" - interpreting images and providing structured findings.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from openai import OpenAI
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
GPT5_MODEL = "openai/gpt-4o"  # GPT-5 via OpenRouter (use latest available model)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Vision prompts
VISION_SYSTEM_PROMPT = """You are a medical image analysis assistant. Your role is to carefully observe and describe medical images with clinical accuracy.

When analyzing an image, provide:
1. A detailed description of what you observe
2. Structured findings in JSON format with relevant medical details
3. Your confidence level in the analysis

Be objective and factual. Note any limitations in image quality or visibility. Never provide definitive diagnoses - only observations and possible considerations for a healthcare provider to evaluate.

Format your response as:
DESCRIPTION: [Your detailed narrative description]

STRUCTURED_FINDINGS: [JSON object with relevant findings]

CONFIDENCE: [HIGH/MEDIUM/LOW with brief justification]"""


def get_vision_prompt(user_context: Optional[str] = None) -> str:
    """
    Build vision analysis prompt with optional user context.
    
    Args:
        user_context: Optional context about the patient or situation
        
    Returns:
        Formatted prompt string
    """
    prompt = "Please analyze this medical image carefully. Describe what you observe in detail."
    
    if user_context:
        prompt += f"\n\nContext: {user_context}"
    
    prompt += "\n\nProvide your analysis in the format specified in the system instructions."
    
    return prompt


def parse_vision_response(response_text: str) -> Dict[str, Any]:
    """
    Parse GPT-5 vision response into structured format.
    
    Args:
        response_text: Raw response from GPT-5
        
    Returns:
        Structured dict with description, findings, and confidence
    """
    try:
        # Initialize result
        result = {
            "description": "",
            "structured_findings": {},
            "confidence": "MEDIUM",
            "raw_response": response_text
        }
        
        # Parse sections
        lines = response_text.strip().split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("DESCRIPTION:"):
                if current_section and section_content:
                    result[current_section] = '\n'.join(section_content).strip()
                current_section = "description"
                section_content = [line.replace("DESCRIPTION:", "").strip()]
            
            elif line.startswith("STRUCTURED_FINDINGS:"):
                if current_section and section_content:
                    result[current_section] = '\n'.join(section_content).strip()
                current_section = "structured_findings"
                section_content = [line.replace("STRUCTURED_FINDINGS:", "").strip()]
            
            elif line.startswith("CONFIDENCE:"):
                if current_section and section_content:
                    if current_section == "structured_findings":
                        # Try to parse JSON
                        try:
                            json_str = '\n'.join(section_content).strip()
                            result["structured_findings"] = json.loads(json_str)
                        except:
                            result["structured_findings"] = {"raw": '\n'.join(section_content).strip()}
                    else:
                        result[current_section] = '\n'.join(section_content).strip()
                
                current_section = "confidence"
                section_content = [line.replace("CONFIDENCE:", "").strip()]
            
            elif line and current_section:
                section_content.append(line)
        
        # Process final section
        if current_section and section_content:
            if current_section == "structured_findings":
                try:
                    json_str = '\n'.join(section_content).strip()
                    result["structured_findings"] = json.loads(json_str)
                except:
                    result["structured_findings"] = {"raw": '\n'.join(section_content).strip()}
            else:
                result[current_section] = '\n'.join(section_content).strip()
        
        # Fallback: if parsing failed, use entire response as description
        if not result["description"] and response_text:
            result["description"] = response_text
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing vision response: {str(e)}")
        return {
            "description": response_text,
            "structured_findings": {},
            "confidence": "MEDIUM",
            "raw_response": response_text,
            "parse_error": str(e)
        }


async def analyze_medical_image(
    image_bytes: bytes,
    user_context: Optional[str] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze medical image using GPT-5 vision (non-streaming).
    
    Args:
        image_bytes: Raw image bytes
        user_context: Optional context about the patient or situation
        filename: Optional filename
        
    Returns:
        Dict with image interpretation results
        
    Raises:
        ImageValidationError: If image validation fails
        Exception: If API call fails
    """
    try:
        logger.info("Starting medical image analysis (non-streaming)")
        
        # Prepare image
        prepared_image = prepare_image_for_api(image_bytes, filename)
        base64_image = prepared_image["base64"]
        
        # Get OpenAI client (configured for OpenRouter)
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # Build prompt
        prompt = get_vision_prompt(user_context)
        
        # Call GPT-5 vision
        logger.info(f"Calling GPT-5 vision model: {GPT5_MODEL}")
        completion = client.chat.completions.create(
            model=GPT5_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": VISION_SYSTEM_PROMPT
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
            max_tokens=1024,
            temperature=0.3  # Lower temperature for more consistent medical analysis
        )
        
        # Extract response
        response_text = completion.choices[0].message.content
        
        # Parse response
        interpretation = parse_vision_response(response_text)
        
        # Add metadata
        interpretation["metadata"] = {
            "model": GPT5_MODEL,
            "timestamp": datetime.utcnow().isoformat(),
            "image_metadata": prepared_image["metadata"],
            "was_resized": prepared_image["was_resized"]
        }
        
        logger.info("Image analysis completed successfully")
        
        return interpretation
        
    except ImageValidationError:
        raise
    except Exception as e:
        logger.error(f"Error in medical image analysis: {str(e)}")
        raise


async def analyze_medical_image_streaming(
    image_bytes: bytes,
    user_context: Optional[str] = None,
    filename: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Analyze medical image using GPT-5 vision with SSE streaming.
    Yields progress events for transparency.
    
    Args:
        image_bytes: Raw image bytes
        user_context: Optional context about the patient or situation
        filename: Optional filename
        
    Yields:
        Dict events with type and data for each processing step
    """
    try:
        # Event 1: Image validation
        yield {
            "type": "image_validation",
            "data": "Validating image format and size...",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Prepare image
        try:
            prepared_image = prepare_image_for_api(image_bytes, filename)
            base64_image = prepared_image["base64"]
            
            # Validation success event
            yield {
                "type": "image_validation",
                "data": (
                    f"Image validated: {prepared_image['metadata']['format']}, "
                    f"{prepared_image['metadata']['width']}x{prepared_image['metadata']['height']}, "
                    f"{prepared_image['processed_size_mb']}MB"
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
        
        # Event 2: Image processing
        if prepared_image["was_resized"]:
            yield {
                "type": "image_processing",
                "data": (
                    f"Image resized for optimal processing "
                    f"({prepared_image['original_size_mb']}MB → {prepared_image['processed_size_mb']}MB)"
                ),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            yield {
                "type": "image_processing",
                "data": "Encoding image for analysis...",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Event 3: Vision analysis start
        yield {
            "type": "vision_analysis",
            "data": "Analyzing image with vision model...",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get OpenAI client
        if not OPENROUTER_API_KEY:
            yield {
                "type": "error",
                "data": "OPENROUTER_API_KEY not configured",
                "timestamp": datetime.utcnow().isoformat()
            }
            return
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # Build prompt
        prompt = get_vision_prompt(user_context)
        
        # Call GPT-5 vision (streaming)
        logger.info(f"Calling GPT-5 vision model (streaming): {GPT5_MODEL}")
        
        stream = client.chat.completions.create(
            model=GPT5_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": VISION_SYSTEM_PROMPT
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
            max_tokens=1024,
            temperature=0.3,
            stream=True
        )
        
        # Accumulate response
        response_text = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
        
        # Parse response
        interpretation = parse_vision_response(response_text)
        
        # Add metadata
        interpretation["metadata"] = {
            "model": GPT5_MODEL,
            "timestamp": datetime.utcnow().isoformat(),
            "image_metadata": prepared_image["metadata"],
            "was_resized": prepared_image["was_resized"]
        }
        
        # Event 4: Vision complete
        yield {
            "type": "vision_complete",
            "data": interpretation,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Image analysis completed successfully (streaming)")
        
    except Exception as e:
        logger.error(f"Error in streaming image analysis: {str(e)}")
        yield {
            "type": "error",
            "data": f"Image analysis failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

