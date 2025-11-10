"""
Service layer for drug authenticity verification.
Handles Tavily search integration and database caching.
"""

import json
import logging
import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

from tavily import TavilyClient
from dotenv import load_dotenv
from sqlmodel import Session, select

from src.database import engine
from src.models.drug_authenticity import DrugAuthenticityCheck
from .schemas import DrugAuthenticityResponse, DetailedReport

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CACHE_EXPIRY_DAYS = 30

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
        logger.info("Initialized Tavily client for drug authenticity search")
    
    return _tavily_client


def normalize_drug_name(drug_name: str) -> str:
    """
    Normalize drug name for consistent cache lookup.
    
    Args:
        drug_name: Drug name to normalize
        
    Returns:
        Normalized drug name (lowercase, trimmed)
    """
    return drug_name.strip().lower()


async def search_drug_with_tavily(drug_name: str) -> Dict[str, Any]:
    """
    Search for drug authenticity information using Tavily API.
    
    Args:
        drug_name: Name of the drug to search
        
    Returns:
        Dictionary with search results
    """
    try:
        client = get_tavily_client()
        
        # Construct comprehensive search query
        search_query = f"drug authenticity verification {drug_name} manufacturer counterfeit FDA approval"
        
        logger.info(f"Executing Tavily search for drug: '{drug_name}'")
        
        # Execute search with advanced depth for thorough verification
        response = client.search(
            query=search_query,
            search_depth="advanced",
            topic="general",
            max_results=7  # Get more results for better verification
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
        
        logger.info(f"Tavily search completed: {len(results)} results found for '{drug_name}'")
        
        return {
            "query": search_query,
            "drug_name": drug_name,
            "results_count": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error executing Tavily search for '{drug_name}': {str(e)}")
        raise


def analyze_search_results(search_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze Tavily search results to determine drug authenticity.
    
    Args:
        search_data: Dictionary containing search results from Tavily
        
    Returns:
        Dictionary with authenticity assessment
    """
    results = search_data.get("results", [])
    drug_name = search_data.get("drug_name", "")
    
    if not results:
        return {
            "status": "unknown",
            "confidence_score": 0.0,
            "detailed_report": {
                "manufacturer_info": None,
                "regulatory_status": "Information not available",
                "warnings": ["No information found. Please consult a healthcare professional."],
                "verification_sources": [],
                "additional_info": "Unable to verify drug authenticity due to lack of information."
            }
        }
    
    # Analysis keywords
    authentic_keywords = [
        "fda approved", "fda approval", "legitimate", "authentic", "approved by", 
        "licensed", "certified", "official", "genuine", "authorized",
        "regulatory approval", "pharmaceutical company"
    ]
    counterfeit_keywords = [
        "counterfeit", "fake", "fraudulent", "unauthorized", "illegal", 
        "recalled", "warning", "alert", "suspicious", "black market",
        "not approved", "unapproved"
    ]
    
    # Aggregate content from all results
    all_content = " ".join([r.get("content", "").lower() for r in results])
    all_titles = " ".join([r.get("title", "").lower() for r in results])
    combined_text = all_content + " " + all_titles
    
    # Count keyword occurrences
    authentic_count = sum(1 for keyword in authentic_keywords if keyword in combined_text)
    counterfeit_count = sum(1 for keyword in counterfeit_keywords if keyword in combined_text)
    
    # Determine status and confidence
    total_indicators = authentic_count + counterfeit_count
    
    if total_indicators == 0:
        status = "unknown"
        confidence = 0.3
    elif counterfeit_count > authentic_count:
        status = "counterfeit"
        confidence = min(0.7 + (counterfeit_count / max(total_indicators, 1)) * 0.3, 0.95)
    else:
        status = "authentic"
        confidence = min(0.6 + (authentic_count / max(total_indicators, 1)) * 0.4, 0.95)
    
    # Extract detailed information
    manufacturer_info = extract_manufacturer_info(results, drug_name)
    regulatory_status = extract_regulatory_status(results)
    warnings = extract_warnings(results, status)
    sources = [r.get("url", "") for r in results[:5] if r.get("url")]
    additional_info = extract_additional_info(results, drug_name)
    
    return {
        "status": status,
        "confidence_score": round(confidence, 2),
        "detailed_report": {
            "manufacturer_info": manufacturer_info,
            "regulatory_status": regulatory_status,
            "warnings": warnings,
            "verification_sources": sources,
            "additional_info": additional_info
        }
    }


def extract_manufacturer_info(results: List[Dict], drug_name: str) -> Optional[str]:
    """Extract manufacturer information from search results"""
    for result in results[:3]:  # Check top 3 results
        content = result.get("content", "")
        
        # Look for manufacturer patterns
        manufacturer_patterns = [
            r'manufactured by ([^.,]+)',
            r'manufacturer[:\s]+([^.,]+)',
            r'produced by ([^.,]+)',
            r'([A-Z][a-zA-Z\s&]+(?:Pharmaceuticals|Pharma|Labs|Inc|Ltd|Corporation))'
        ]
        
        for pattern in manufacturer_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    return None


def extract_regulatory_status(results: List[Dict]) -> str:
    """Extract FDA or regulatory approval status"""
    for result in results[:5]:
        content = result.get("content", "").lower()
        
        if "fda approved" in content or "fda approval" in content:
            return "FDA approved"
        elif "fda authorized" in content:
            return "FDA authorized"
        elif "approved by" in content:
            return "Regulatory approval found"
    
    return "Regulatory status unclear - consult official sources"


def extract_warnings(results: List[Dict], status: str) -> List[str]:
    """Extract relevant warnings from search results"""
    warnings = []
    
    # Add status-based warnings
    if status == "counterfeit":
        warnings.append("⚠️ CRITICAL: Potential counterfeit drug detected. Do not use.")
        warnings.append("Purchase only from licensed pharmacies and authorized distributors.")
    elif status == "unknown":
        warnings.append("Unable to verify authenticity. Exercise caution.")
    
    # Extract specific warnings from content
    warning_keywords = ["warning", "caution", "alert", "recalled", "side effect", "contraindication"]
    
    for result in results[:3]:
        content = result.get("content", "").lower()
        for keyword in warning_keywords:
            if keyword in content:
                # Extract sentence containing the warning
                sentences = content.split('.')
                for sentence in sentences:
                    if keyword in sentence and len(sentence.strip()) > 20:
                        warnings.append(sentence.strip().capitalize())
                        break
    
    # Default warnings if none found
    if not warnings:
        warnings.append("Always consult a healthcare professional before use.")
        warnings.append("Purchase medications from licensed and reputable sources.")
    
    # Limit to 5 most relevant warnings
    return warnings[:5]


def extract_additional_info(results: List[Dict], drug_name: str) -> Optional[str]:
    """Extract additional relevant information"""
    if results:
        # Use the first result's content as additional context
        first_result = results[0]
        content = first_result.get("content", "")
        
        # Return first 200 characters as a summary
        if content:
            summary = content[:300].strip()
            if len(content) > 300:
                summary += "..."
            return summary
    
    return None


async def check_drug_authenticity(drug_name: str) -> DrugAuthenticityResponse:
    """
    Check drug authenticity with caching.
    
    Args:
        drug_name: Name of the drug to verify
        
    Returns:
        DrugAuthenticityResponse with verification results
    """
    drug_name_normalized = normalize_drug_name(drug_name)
    
    logger.info(f"Checking drug authenticity for: '{drug_name}'")
    
    # Check cache first
    with Session(engine) as session:
        statement = select(DrugAuthenticityCheck).where(
            DrugAuthenticityCheck.drug_name_normalized == drug_name_normalized
        ).order_by(DrugAuthenticityCheck.search_timestamp.desc())
        
        cached_result = session.exec(statement).first()
        
        # Return cached result if valid and not expired
        if cached_result and not cached_result.is_expired():
            logger.info(f"Returning cached result for '{drug_name}'")
            
            return DrugAuthenticityResponse(
                status=cached_result.authenticity_status.lower(),
                confidence_score=float(cached_result.confidence_score),
                drug_name=cached_result.drug_name,
                detailed_report=DetailedReport(**cached_result.detailed_report),
                cached=True,
                search_timestamp=cached_result.search_timestamp,
                message="Result retrieved from cache"
            )
    
    # Perform new search
    logger.info(f"Cache miss or expired. Performing new search for '{drug_name}'")
    
    try:
        search_data = await search_drug_with_tavily(drug_name)
        analysis = analyze_search_results(search_data)
        
        # Save to database
        with Session(engine) as session:
            new_check = DrugAuthenticityCheck(
                drug_name=drug_name,
                drug_name_normalized=drug_name_normalized,
                search_query=search_data.get("query", ""),
                authenticity_status=analysis["status"].upper(),
                confidence_score=Decimal(str(analysis["confidence_score"])),
                detailed_report=analysis["detailed_report"],
                sources=analysis["detailed_report"]["verification_sources"],
                search_timestamp=datetime.utcnow(),
                expires_at=DrugAuthenticityCheck.calculate_expiry_date(CACHE_EXPIRY_DAYS)
            )
            
            session.add(new_check)
            session.commit()
            session.refresh(new_check)
            
            logger.info(f"Saved new authenticity check result for '{drug_name}'")
            
            return DrugAuthenticityResponse(
                status=analysis["status"],
                confidence_score=analysis["confidence_score"],
                drug_name=drug_name,
                detailed_report=DetailedReport(**analysis["detailed_report"]),
                cached=False,
                search_timestamp=new_check.search_timestamp,
                message="Drug authenticity verified successfully"
            )
    
    except Exception as e:
        logger.error(f"Error checking drug authenticity for '{drug_name}': {str(e)}")
        raise

