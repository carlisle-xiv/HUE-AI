"""
Drug suggester router with API endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from src.database import get_db
from .schemas import (
    DrugSuggestionRequest,
    DrugSuggestionResponse,
    ErrorResponse
)
from .service import process_drug_suggestion_request

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/drug-suggester",
    tags=["Drug Suggester"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/suggest",
    response_model=DrugSuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Intelligent Drug Suggestions",
    description="""
    **Intelligent Drug Suggester for Doctors**
    
    This endpoint provides AI-powered drug recommendations based on:
    - Patient's diagnosis and medical history
    - Drug-drug interactions (via RxNav API)
    - Drug-allergy interactions
    - Drug-condition contraindications
    - Ghana Standard Treatment Guidelines
    - Ghana Essential Medicine List
    - Facility pharmacy inventory availability
    
    **Process:**
    1. Gathers comprehensive patient context (conditions, allergies, current medications, vitals)
    2. Searches Ghana STG and Essential Medicine List via Tavily
    3. Checks drug interactions using RxNav API (with caching)
    4. Queries facility pharmacy inventories
    5. Uses AI (GPT-4) to generate appropriate drug suggestions with dosing
    6. Validates all suggestions for safety
    7. Returns primary suggestions (in-stock) and alternates
    
    **Safety Features:**
    - Automatic allergy checking
    - Drug interaction detection
    - Contraindication verification
    - Audit trail for all suggestions
    
    **Response includes:**
    - Primary drug suggestions (available in facility inventory)
    - Alternate drug suggestions (not in stock but clinically appropriate)
    - Detailed dosing with rationale
    - Allergy alerts
    - Interaction warnings
    - Ghana guideline notes
    
    **Note:** These are AI-generated suggestions. Final prescribing decisions 
    should be made by the healthcare provider based on comprehensive clinical evaluation.
    """,
    responses={
        200: {
            "description": "Drug suggestions generated successfully",
            "model": DrugSuggestionResponse
        },
        400: {
            "description": "Invalid request",
            "model": ErrorResponse
        },
        404: {
            "description": "Patient or doctor not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
async def suggest_drugs(
    request: DrugSuggestionRequest,
    db: Session = Depends(get_db)
) -> DrugSuggestionResponse:
    """
    Generate intelligent drug suggestions for a patient's diagnosis.
    
    Args:
        request: DrugSuggestionRequest with patient_id, diagnosis, doctor_id, etc.
        db: Database session
        
    Returns:
        DrugSuggestionResponse with primary and alternate drug suggestions
        
    Raises:
        HTTPException: If patient/doctor not found or processing fails
    """
    try:
        logger.info(
            f"Drug suggestion request received: "
            f"patient={request.patient_id}, diagnosis='{request.diagnosis}', "
            f"doctor={request.doctor_id}"
        )
        
        # Process the request
        response = await process_drug_suggestion_request(request, db)
        
        logger.info(
            f"Drug suggestion completed: "
            f"{len(response.primary_suggestions)} primary, "
            f"{len(response.alternate_suggestions)} alternate suggestions"
        )
        
        return response
        
    except ValueError as e:
        # Patient or doctor not found
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(
            f"Error processing drug suggestion request: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate drug suggestions: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health Check",
    description="Check if the drug suggester service is operational",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
async def health_check():
    """
    Health check endpoint for drug suggester service.
    
    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "service": "drug-suggester",
        "message": "Drug suggester service is operational",
        "features": [
            "Patient context gathering",
            "RxNav drug interaction checking",
            "Ghana STG/EML integration",
            "Facility inventory checking",
            "AI-powered dosing recommendations",
            "Allergy and contraindication checking"
        ]
    }


@router.get(
    "/",
    summary="Service Information",
    description="Get information about the drug suggester service",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
async def service_info():
    """
    Get information about the drug suggester service.
    
    Returns:
        Service information and capabilities
    """
    return {
        "service": "Intelligent Drug Suggester",
        "version": "1.0.0",
        "description": "AI-powered drug recommendation system for doctors in Ghana",
        "features": {
            "patient_analysis": [
                "Medical history review",
                "Active condition tracking",
                "Allergy checking",
                "Current medication review",
                "Vital signs consideration"
            ],
            "safety_checks": [
                "Drug-drug interaction detection (RxNav API)",
                "Drug-allergy checking",
                "Contraindication verification",
                "Multi-facility inventory checking"
            ],
            "guidelines": [
                "Ghana Standard Treatment Guidelines",
                "Ghana Essential Medicine List",
                "Evidence-based recommendations"
            ],
            "ai_capabilities": [
                "Intelligent drug selection",
                "Personalized dosing recommendations",
                "Clinical rationale generation",
                "Alternative suggestions"
            ]
        },
        "integrations": {
            "rxnav": "NIH RxNav API for drug interactions and normalization",
            "tavily": "Web search for Ghana treatment guidelines",
            "openrouter": "GPT-4 for intelligent recommendations"
        },
        "endpoints": {
            "POST /suggest": "Generate drug suggestions for a patient",
            "GET /health": "Service health check",
            "GET /": "Service information"
        },
        "safety_disclaimer": [
            "AI-generated suggestions require clinical validation",
            "Always verify against current guidelines",
            "Consider individual patient factors",
            "Final prescribing is physician's responsibility"
        ]
    }

