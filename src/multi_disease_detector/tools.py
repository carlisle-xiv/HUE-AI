from typing import List, Dict, Any

# Tool definitions in OpenRouter/OpenAI format
TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tavily_web_search",
            "description": (
                "Search the web for current medical information, research studies, "
                "drug interactions, treatment guidelines, and health-related topics. "
                "Use this when you need up-to-date information not in your training data, "
                "or when the user asks about recent medical developments, specific medications, "
                "or current health guidelines."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The search query. Be specific and include medical terms. "
                            "Examples: 'latest cholesterol treatment guidelines 2025', "
                            "'metformin side effects and contraindications', "
                            "'symptoms of iron deficiency anemia'"
                        )
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "description": (
                            "Search depth. 'basic' for quick searches (faster, fewer sources). "
                            "'advanced' for comprehensive searches (slower, more sources). "
                            "Default: 'basic'"
                        ),
                        "default": "basic"
                    },
                    "topic": {
                        "type": "string",
                        "enum": ["general", "news", "finance"],
                        "description": (
                            "Topic category for search optimization. "
                            "Use 'general' for medical and health-related queries. "
                            "'news' for recent updates, 'finance' for financial topics. Default: 'general'"
                        ),
                        "default": "general"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_lab_explanation",
            "description": (
                "Generate a detailed, structured explanation of laboratory test results. "
                "Use this when the user provides lab values or asks for interpretation of "
                "blood work, urinalysis, metabolic panels, or other lab tests. "
                "Creates a professional medical document with normal ranges, interpretations, "
                "and clinical significance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "test_type": {
                        "type": "string",
                        "description": (
                            "Type of lab test. Examples: 'Complete Blood Count (CBC)', "
                            "'Lipid Panel', 'Comprehensive Metabolic Panel', "
                            "'Thyroid Function Tests', 'Hemoglobin A1c'"
                        )
                    },
                    "test_results": {
                        "type": "object",
                        "description": (
                            "Test results as key-value pairs. Keys are test names, "
                            "values are the results with units. "
                            "Example: {'Total Cholesterol': '240 mg/dL', 'LDL': '160 mg/dL', 'HDL': '35 mg/dL'}"
                        )
                    },
                    "patient_context": {
                        "type": "string",
                        "description": (
                            "Optional patient context like age, gender, existing conditions, "
                            "or symptoms that may help with interpretation. "
                            "Example: '45-year-old male with family history of heart disease'"
                        )
                    }
                },
                "required": ["test_type", "test_results"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_imaging_explanation",
            "description": (
                "Generate a detailed explanation of medical imaging results (X-rays, CT scans, MRI, etc.). "
                "Use this when the user describes imaging findings or asks for help understanding "
                "radiology reports. Creates an educational document explaining findings in layman's terms "
                "with clinical context and recommendations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "imaging_type": {
                        "type": "string",
                        "description": (
                            "Type of imaging study. Examples: 'Chest X-ray', 'Abdominal CT', "
                            "'Brain MRI', 'Knee MRI', 'Mammogram', 'Ultrasound'"
                        )
                    },
                    "findings": {
                        "type": "string",
                        "description": (
                            "Description of the imaging findings, either from a report or "
                            "as described by the patient. Can include technical terms or lay descriptions."
                        )
                    },
                    "clinical_indication": {
                        "type": "string",
                        "description": (
                            "Reason for the imaging study. Examples: 'Persistent cough', "
                            "'Abdominal pain', 'Follow-up after treatment', 'Screening'"
                        )
                    },
                    "patient_context": {
                        "type": "string",
                        "description": (
                            "Optional patient context like age, relevant medical history, "
                            "or symptoms that may help with interpretation."
                        )
                    }
                },
                "required": ["imaging_type", "findings"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_medical_summary",
            "description": (
                "Generate a comprehensive medical summary or educational document about "
                "a health condition, treatment, or medical topic. Use this when the user "
                "asks for detailed information about a disease, treatment options, "
                "prevention strategies, or wants to understand a medical concept better."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "The medical topic or condition to explain. "
                            "Examples: 'Type 2 Diabetes', 'Hypertension management', "
                            "'Asthma treatment options', 'COVID-19 prevention'"
                        )
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Specific aspects to focus on. Options: 'symptoms', 'causes', "
                            "'diagnosis', 'treatment', 'prevention', 'complications', "
                            "'lifestyle', 'prognosis'. Leave empty for comprehensive overview."
                        )
                    },
                    "patient_context": {
                        "type": "string",
                        "description": (
                            "Optional patient context to personalize the summary. "
                            "Example: 'Recently diagnosed', 'Family history', 'Specific concerns about medication side effects'"
                        )
                    }
                },
                "required": ["topic"]
            }
        }
    }
]


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all available tool definitions for the AI assistant.
    
    Returns:
        List of tool definitions in OpenRouter/OpenAI format
    """
    return TOOL_DEFINITIONS


def get_tool_names() -> List[str]:
    """
    Get list of available tool names.
    
    Returns:
        List of tool names
    """
    return [tool["function"]["name"] for tool in TOOL_DEFINITIONS]


def get_tool_definition(tool_name: str) -> Dict[str, Any]:
    """
    Get definition for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool definition dict or None if not found
    """
    for tool in TOOL_DEFINITIONS:
        if tool["function"]["name"] == tool_name:
            return tool
    return None

