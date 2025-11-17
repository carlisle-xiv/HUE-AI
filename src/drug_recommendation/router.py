import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from .schemas import (
    DrugAuthenticityRequest,
    DrugAuthenticityResponse,
    ErrorResponse
)
from .service import check_drug_authenticity

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/drug-authenticity",
    tags=["Drug Authenticity"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/check",
    response_model=DrugAuthenticityResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Drug Authenticity",
    description="""
    Verify the authenticity of a drug using web search and multiple verification sources.
    
    This endpoint:
    - Searches trusted sources for drug information
    - Verifies manufacturer and regulatory approval status
    - Checks for counterfeit alerts and warnings
    - Returns both simple status (authentic/counterfeit/unknown) and detailed report
    - Caches results for 30 days to improve performance
    
    **Response includes:**
    - Authentication status with confidence score
    - Detailed manufacturer information
    - FDA/regulatory approval status
    - Important warnings and alerts
    - Verification sources (URLs)
    - Cache status and search timestamp
    
    **Note:** This is an automated verification tool. Always purchase medications from 
    licensed pharmacies and consult healthcare professionals for medical advice.
    """,
    responses={
        200: {
            "description": "Drug authenticity verified successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "authentic",
                        "confidence_score": 0.85,
                        "drug_name": "Paracetamol",
                        "detailed_report": {
                            "manufacturer_info": "Johnson & Johnson",
                            "regulatory_status": "FDA approved",
                            "warnings": [
                                "Do not exceed recommended dosage",
                                "May cause liver damage if taken with alcohol"
                            ],
                            "verification_sources": [
                                "https://www.fda.gov/drugs",
                                "https://www.drugs.com/paracetamol.html"
                            ],
                            "additional_info": "Commonly used for pain relief and fever reduction"
                        },
                        "cached": True,
                        "search_timestamp": "2025-11-06T10:30:00Z",
                        "message": "Drug authenticity verified successfully"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
async def verify_drug_authenticity(
    request: DrugAuthenticityRequest
) -> DrugAuthenticityResponse:
    """
    Verify the authenticity of a drug.
    
    Args:
        request: DrugAuthenticityRequest containing drug name
        
    Returns:
        DrugAuthenticityResponse with verification results
        
    Raises:
        HTTPException: If verification fails or invalid request
    """
    try:
        logger.info(f"Received drug authenticity check request for: '{request.drug_name}'")
        
        # Perform authenticity check
        result = await check_drug_authenticity(request.drug_name)
        
        logger.info(
            f"Drug authenticity check completed for '{request.drug_name}': "
            f"status={result.status}, confidence={result.confidence_score}, cached={result.cached}"
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error for drug '{request.drug_name}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(
            f"Error processing drug authenticity check for '{request.drug_name}': {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify drug authenticity: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health Check",
    description="Check if the drug authenticity service is operational",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
async def health_check():
    """
    Health check endpoint for drug authenticity service.
    
    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "service": "drug-authenticity",
        "message": "Drug authenticity verification service is operational"
    }


@router.get(
    "/",
    summary="Service Information",
    description="Get information about the drug authenticity verification service",
    response_model=dict,
    status_code=status.HTTP_200_OK
)
async def service_info():
    """
    Get information about the drug authenticity service.
    
    Returns:
        Service information and capabilities
    """
    return {
        "service": "Drug Authenticity Verification",
        "version": "1.0.0",
        "description": "Verify drug authenticity using web search and multiple verification sources",
        "features": [
            "Automated web search for drug information",
            "Manufacturer verification",
            "FDA/regulatory status checking",
            "Counterfeit alert detection",
            "30-day result caching for performance",
            "Confidence scoring",
            "Multiple verification sources"
        ],
        "endpoints": {
            "POST /check": "Verify drug authenticity",
            "GET /health": "Service health check",
            "GET /": "Service information"
        },
        "notes": [
            "Always purchase medications from licensed pharmacies",
            "Consult healthcare professionals for medical advice",
            "This is an automated tool - use as a reference only"
        ]
    }

