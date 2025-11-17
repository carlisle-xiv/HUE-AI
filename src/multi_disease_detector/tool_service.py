import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from tavily import TavilyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Initialize Tavily client
_tavily_client = None


def get_tavily_client() -> TavilyClient:
    """
    Get or initialize the Tavily client.
    
    Returns:
        TavilyClient instance
        
    Raises:
        ValueError: If TAVILY_API_KEY is not set
    """
    global _tavily_client
    
    if _tavily_client is None:
        if not TAVILY_API_KEY:
            logger.error("TAVILY_API_KEY not found in environment variables")
            raise ValueError("TAVILY_API_KEY is required. Please set it in your .env file")
        
        _tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        logger.info("Initialized Tavily client for medical web search")
    
    return _tavily_client


async def execute_tavily_search(
    query: str,
    search_depth: str = "basic",
    topic: str = "general"
) -> str:
    """
    Execute a web search using Tavily API.
    
    Args:
        query: Search query
        search_depth: Search depth - "basic" or "advanced"
        topic: Topic category - "general", "news", or "finance"
        
    Returns:
        JSON string with search results
    """
    try:
        client = get_tavily_client()
        
        logger.info(f"Executing Tavily search: query='{query}', depth={search_depth}, topic={topic}")
        
        # Execute search with appropriate parameters
        response = client.search(
            query=query,
            search_depth=search_depth,
            topic=topic,
            max_results=5  # Limit results to keep context manageable
        )
        
        # Extract relevant information
        results = []
        for result in response.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0)
            })
        
        # Format response
        search_result = {
            "query": query,
            "results_count": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Tavily search completed: {len(results)} results found")
        
        return json.dumps(search_result, indent=2)
        
    except Exception as e:
        logger.error(f"Error executing Tavily search: {str(e)}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "query": query,
            "timestamp": datetime.utcnow().isoformat()
        })


async def generate_lab_explanation_content(
    test_type: str,
    test_results: Dict[str, Any],
    patient_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate content for lab explanation artifact.
    This prepares the data structure; the AI will fill in the actual explanation.
    
    Args:
        test_type: Type of lab test
        test_results: Test results as key-value pairs
        patient_context: Optional patient context
        
    Returns:
        Structured artifact data ready for AI to populate
    """
    logger.info(f"Generating lab explanation content for: {test_type}")
    
    artifact = {
        "type": "lab_explanation",
        "test_type": test_type,
        "test_results": test_results,
        "patient_context": patient_context,
        "timestamp": datetime.utcnow().isoformat(),
        "instruction": (
            "Please analyze these lab results and provide a comprehensive explanation including: "
            "1) Overview of what each test measures, "
            "2) Whether values are normal/abnormal and by how much, "
            "3) Clinical significance and what it might indicate, "
            "4) Recommendations for next steps or follow-up, "
            "5) Important disclaimers about consulting healthcare providers."
        )
    }
    
    return artifact


async def generate_imaging_explanation_content(
    imaging_type: str,
    findings: str,
    clinical_indication: Optional[str] = None,
    patient_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate content for imaging explanation artifact.
    This prepares the data structure; the AI will fill in the actual explanation.
    
    Args:
        imaging_type: Type of imaging study
        findings: Description of findings
        clinical_indication: Reason for the imaging
        patient_context: Optional patient context
        
    Returns:
        Structured artifact data ready for AI to populate
    """
    logger.info(f"Generating imaging explanation content for: {imaging_type}")
    
    artifact = {
        "type": "imaging_analysis",
        "imaging_type": imaging_type,
        "findings": findings,
        "clinical_indication": clinical_indication,
        "patient_context": patient_context,
        "timestamp": datetime.utcnow().isoformat(),
        "instruction": (
            "Please analyze these imaging findings and provide a comprehensive explanation including: "
            "1) What the imaging study is and what it's used for, "
            "2) Explanation of the findings in simple terms, "
            "3) What these findings might indicate clinically, "
            "4) Typical next steps or follow-up recommendations, "
            "5) Important disclaimers about the need for professional interpretation."
        )
    }
    
    return artifact


async def generate_medical_summary_content(
    topic: str,
    focus_areas: Optional[List[str]] = None,
    patient_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate content for medical summary artifact.
    This prepares the data structure; the AI will fill in the actual summary.
    
    Args:
        topic: Medical topic or condition
        focus_areas: Specific aspects to focus on
        patient_context: Optional patient context
        
    Returns:
        Structured artifact data ready for AI to populate
    """
    logger.info(f"Generating medical summary content for: {topic}")
    
    artifact = {
        "type": "medical_summary",
        "topic": topic,
        "focus_areas": focus_areas or [],
        "patient_context": patient_context,
        "timestamp": datetime.utcnow().isoformat(),
        "instruction": (
            "Please create a comprehensive medical summary covering the requested topic. "
            f"Focus areas: {', '.join(focus_areas) if focus_areas else 'comprehensive overview'}. "
            "Include: relevant medical information, evidence-based recommendations, "
            "lifestyle considerations, and appropriate medical disclaimers."
        )
    }
    
    return artifact


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Route tool execution to the appropriate handler.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        
    Returns:
        Tool execution result as JSON string
    """
    logger.info(f"Executing tool: {tool_name}")
    
    try:
        if tool_name == "tavily_web_search":
            return await execute_tavily_search(
                query=arguments.get("query"),
                search_depth=arguments.get("search_depth", "basic"),
                topic=arguments.get("topic", "medical")
            )
        
        elif tool_name == "generate_lab_explanation":
            result = await generate_lab_explanation_content(
                test_type=arguments.get("test_type"),
                test_results=arguments.get("test_results"),
                patient_context=arguments.get("patient_context")
            )
            return json.dumps(result, indent=2)
        
        elif tool_name == "generate_imaging_explanation":
            result = await generate_imaging_explanation_content(
                imaging_type=arguments.get("imaging_type"),
                findings=arguments.get("findings"),
                clinical_indication=arguments.get("clinical_indication"),
                patient_context=arguments.get("patient_context")
            )
            return json.dumps(result, indent=2)
        
        elif tool_name == "generate_medical_summary":
            result = await generate_medical_summary_content(
                topic=arguments.get("topic"),
                focus_areas=arguments.get("focus_areas"),
                patient_context=arguments.get("patient_context")
            )
            return json.dumps(result, indent=2)
        
        else:
            error_msg = f"Unknown tool: {tool_name}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
            
    except Exception as e:
        error_msg = f"Error executing tool {tool_name}: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

