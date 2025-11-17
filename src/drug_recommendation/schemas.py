from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class DrugAuthenticityRequest(BaseModel):
    """Request schema for drug authenticity check"""
    
    drug_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the drug to verify",
        examples=["Paracetamol", "Ibuprofen", "Amoxicillin"]
    )
    
    @field_validator('drug_name')
    @classmethod
    def validate_drug_name(cls, v: str) -> str:
        """Validate and clean drug name"""
        if not v or not v.strip():
            raise ValueError("Drug name cannot be empty")
        return v.strip()


class DetailedReport(BaseModel):
    """Detailed drug authenticity report"""
    
    manufacturer_info: Optional[str] = Field(
        None,
        description="Information about the drug manufacturer"
    )
    regulatory_status: Optional[str] = Field(
        None,
        description="FDA/regulatory approval status"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Important warnings or alerts about the drug"
    )
    verification_sources: List[str] = Field(
        default_factory=list,
        description="URLs of sources used for verification"
    )
    additional_info: Optional[str] = Field(
        None,
        description="Additional relevant information"
    )


class DrugAuthenticityResponse(BaseModel):
    """Response schema for drug authenticity check"""
    
    status: str = Field(
        ...,
        description="Authenticity status: 'authentic', 'counterfeit', or 'unknown'",
        examples=["authentic", "counterfeit", "unknown"]
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the authenticity assessment (0.0 to 1.0)"
    )
    drug_name: str = Field(
        ...,
        description="Name of the drug that was verified"
    )
    detailed_report: DetailedReport = Field(
        ...,
        description="Detailed information about the drug"
    )
    cached: bool = Field(
        ...,
        description="Whether this result was retrieved from cache"
    )
    search_timestamp: datetime = Field(
        ...,
        description="Timestamp when the search was performed"
    )
    message: Optional[str] = Field(
        None,
        description="Additional message or notes"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "authentic",
                "confidence_score": 0.85,
                "drug_name": "Paracetamol",
                "detailed_report": {
                    "manufacturer_info": "Manufactured by Johnson & Johnson",
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


class ErrorResponse(BaseModel):
    """Error response schema"""
    
    error: str = Field(
        ...,
        description="Error message"
    )
    detail: Optional[str] = Field(
        None,
        description="Detailed error information"
    )
    drug_name: Optional[str] = Field(
        None,
        description="Drug name from the request"
    )

