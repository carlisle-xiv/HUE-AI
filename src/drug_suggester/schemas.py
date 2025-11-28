"""
Schemas for drug suggester API requests and responses.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DrugSuggestionRequest(BaseModel):
    """Request for drug suggestions"""
    
    patient_id: UUID = Field(..., description="Patient ID")
    diagnosis: str = Field(..., description="Primary diagnosis for treatment", min_length=1, max_length=500)
    additional_conditions: Optional[List[str]] = Field(
        default=None,
        description="Other conditions to consider in treatment"
    )
    doctor_id: UUID = Field(..., description="Requesting doctor ID")
    facility_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Facilities to check inventory. If None, checks all facilities"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "diagnosis": "Type 2 Diabetes Mellitus",
                "additional_conditions": ["Hypertension", "Hyperlipidemia"],
                "doctor_id": "660e8400-e29b-41d4-a716-446655440001",
                "facility_ids": ["770e8400-e29b-41d4-a716-446655440002"]
            }
        }


class FacilityInventory(BaseModel):
    """Facility inventory information"""
    
    pharmacy_id: UUID = Field(..., description="Pharmacy/facility ID")
    pharmacy_name: str = Field(..., description="Pharmacy name")
    quantity_available: int = Field(..., description="Available quantity")
    unit_price: float = Field(..., description="Price per unit")
    expiry_date: Optional[str] = Field(None, description="Expiry date (ISO format)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pharmacy_id": "880e8400-e29b-41d4-a716-446655440003",
                "pharmacy_name": "Main Hospital Pharmacy",
                "quantity_available": 500,
                "unit_price": 2.50,
                "expiry_date": "2026-12-31"
            }
        }


class DrugSuggestion(BaseModel):
    """Individual drug suggestion"""
    
    drug_code_id: UUID = Field(..., description="Pharmacy code ID")
    drug_name: str = Field(..., description="Brand/trade name")
    generic_name: Optional[str] = Field(None, description="Generic name")
    dosage: str = Field(..., description="Recommended dosage (e.g., 500mg)")
    frequency: str = Field(..., description="Frequency (e.g., twice daily)")
    duration: str = Field(..., description="Duration (e.g., 7 days)")
    route: Optional[str] = Field(None, description="Route of administration (e.g., oral, IV)")
    in_facility_inventory: bool = Field(..., description="Whether drug is in facility inventory")
    available_facilities: List[FacilityInventory] = Field(
        default=[],
        description="Facilities where drug is available"
    )
    selection_rationale: str = Field(..., description="Why this drug was chosen")
    dosage_rationale: str = Field(..., description="Why this specific dose")
    contraindication_checked: bool = Field(..., description="Whether contraindications were checked")
    interaction_status: str = Field(
        ...,
        description="Interaction status: safe, minor, moderate, severe"
    )
    interaction_details: Optional[str] = Field(
        None,
        description="Details about any interactions found"
    )
    allergy_safe: bool = Field(..., description="Whether drug is safe given patient allergies")
    
    class Config:
        json_schema_extra = {
            "example": {
                "drug_code_id": "990e8400-e29b-41d4-a716-446655440004",
                "drug_name": "Metformin",
                "generic_name": "Metformin Hydrochloride",
                "dosage": "500mg",
                "frequency": "Twice daily",
                "duration": "Continuous (chronic management)",
                "route": "Oral",
                "in_facility_inventory": True,
                "available_facilities": [
                    {
                        "pharmacy_id": "880e8400-e29b-41d4-a716-446655440003",
                        "pharmacy_name": "Main Hospital Pharmacy",
                        "quantity_available": 500,
                        "unit_price": 2.50,
                        "expiry_date": "2026-12-31"
                    }
                ],
                "selection_rationale": "First-line treatment for Type 2 Diabetes per Ghana STG. Reduces hepatic glucose production and improves insulin sensitivity.",
                "dosage_rationale": "Starting dose of 500mg BID with meals to minimize GI side effects. Can be titrated up based on response and tolerance.",
                "contraindication_checked": True,
                "interaction_status": "safe",
                "interaction_details": None,
                "allergy_safe": True
            }
        }


class DrugSuggestionResponse(BaseModel):
    """Response with drug suggestions"""
    
    patient_id: UUID = Field(..., description="Patient ID")
    patient_name: str = Field(..., description="Patient name")
    diagnosis: str = Field(..., description="Primary diagnosis")
    additional_conditions: Optional[List[str]] = Field(None, description="Additional conditions considered")
    
    primary_suggestions: List[DrugSuggestion] = Field(
        ...,
        description="Primary drug suggestions (in facility inventory)"
    )
    alternate_suggestions: List[DrugSuggestion] = Field(
        ...,
        description="Alternate drug suggestions (not in facility inventory)"
    )
    
    allergy_alerts: List[str] = Field(
        default=[],
        description="Active allergy alerts for the patient"
    )
    interaction_warnings: List[str] = Field(
        default=[],
        description="Drug interaction warnings"
    )
    contraindication_alerts: List[str] = Field(
        default=[],
        description="Contraindication alerts"
    )
    
    current_medications: List[str] = Field(
        default=[],
        description="Patient's current medications (checked for interactions)"
    )
    
    ghana_guideline_notes: Optional[str] = Field(
        None,
        description="Relevant Ghana Standard Treatment Guideline notes"
    )
    
    generated_at: datetime = Field(..., description="Timestamp of suggestion generation")
    processing_time_seconds: Optional[float] = Field(
        None,
        description="Time taken to generate suggestions"
    )
    
    facilities_checked: Optional[List[str]] = Field(
        None,
        description="List of facility names checked for inventory"
    )
    
    rxnav_used: bool = Field(..., description="Whether RxNav API was successfully used")
    disclaimer: str = Field(
        default="These are AI-generated suggestions. Final prescribing decisions should be made by the healthcare provider based on comprehensive clinical evaluation.",
        description="Medical disclaimer"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "550e8400-e29b-41d4-a716-446655440000",
                "patient_name": "John Doe",
                "diagnosis": "Type 2 Diabetes Mellitus",
                "additional_conditions": ["Hypertension"],
                "primary_suggestions": [
                    {
                        "drug_code_id": "990e8400-e29b-41d4-a716-446655440004",
                        "drug_name": "Metformin",
                        "generic_name": "Metformin Hydrochloride",
                        "dosage": "500mg",
                        "frequency": "Twice daily",
                        "duration": "Continuous",
                        "route": "Oral",
                        "in_facility_inventory": True,
                        "available_facilities": [],
                        "selection_rationale": "First-line treatment per Ghana STG",
                        "dosage_rationale": "Standard starting dose",
                        "contraindication_checked": True,
                        "interaction_status": "safe",
                        "interaction_details": None,
                        "allergy_safe": True
                    }
                ],
                "alternate_suggestions": [],
                "allergy_alerts": [],
                "interaction_warnings": [],
                "contraindication_alerts": [],
                "current_medications": ["Lisinopril 10mg daily"],
                "ghana_guideline_notes": "Per Ghana STG, Metformin is first-line for T2DM management.",
                "generated_at": "2025-11-25T15:30:00Z",
                "processing_time_seconds": 3.5,
                "facilities_checked": ["Main Hospital Pharmacy"],
                "rxnav_used": True,
                "disclaimer": "These are AI-generated suggestions..."
            }
        }


class ErrorResponse(BaseModel):
    """Error response"""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Patient not found",
                "detail": "No patient exists with the provided ID",
                "timestamp": "2025-11-25T15:30:00Z"
            }
        }

