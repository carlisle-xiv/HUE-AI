"""
Drug suggester models for patient allergies, drug interactions, and suggestion history.
"""

from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Integer, Boolean, DECIMAL, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB


class PatientAllergy(SQLModel, table=True):
    """Patient allergy tracking"""
    
    __tablename__ = "patient_allergies"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    allergen_name: str = Field(max_length=255, index=True)  # Drug name, substance, or food
    allergen_type: str = Field(max_length=50, index=True)  # DRUG, FOOD, ENVIRONMENTAL, OTHER
    severity: str = Field(max_length=20, index=True)  # MILD, MODERATE, SEVERE, LIFE_THREATENING
    reaction_type: Optional[str] = Field(default=None, max_length=100)  # rash, anaphylaxis, nausea, etc.
    reaction_description: Optional[str] = Field(default=None, sa_column=Column(Text))
    diagnosed_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    diagnosed_by_id: Optional[UUID] = Field(default=None, foreign_key="doctors.id")
    is_active: bool = Field(default=True, index=True)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="allergies")
    diagnosed_by: Optional["Doctor"] = Relationship(back_populates="diagnosed_allergies")


class DrugInteractionCache(SQLModel, table=True):
    """Cache for RxNav drug interaction checks"""
    
    __tablename__ = "drug_interaction_cache"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    drug1_rxcui: str = Field(max_length=50, index=True)  # RxNorm Concept Unique Identifier
    drug2_rxcui: str = Field(max_length=50, index=True)
    drug1_name: str = Field(max_length=255)
    drug2_name: str = Field(max_length=255)
    interaction_severity: Optional[str] = Field(default=None, max_length=20)  # MINOR, MODERATE, SEVERE, CONTRAINDICATED
    interaction_description: Optional[str] = Field(default=None, sa_column=Column(Text))
    source: str = Field(default="RxNav", max_length=50)  # RxNav, AI, Manual
    checked_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    expires_at: datetime = Field(index=True)  # 7-day cache expiry
    raw_response: Optional[dict] = Field(default=None, sa_column=Column(JSONB))  # Store full RxNav response
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @staticmethod
    def calculate_expiry_date(days: int = 7) -> datetime:
        """Calculate expiry date from now"""
        return datetime.utcnow() + timedelta(days=days)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.utcnow() > self.expires_at


class DrugSuggestion(SQLModel, table=True):
    """Drug suggestion history for audit trail and learning"""
    
    __tablename__ = "drug_suggestions"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    doctor_id: UUID = Field(foreign_key="doctors.id", index=True)
    diagnosis: str = Field(max_length=500, index=True)
    additional_conditions: Optional[list[str]] = Field(default=None, sa_column=Column(JSONB))
    
    # Suggested drugs
    primary_suggestions: dict = Field(sa_column=Column(JSONB))  # Drugs in facility inventory
    alternate_suggestions: dict = Field(sa_column=Column(JSONB))  # Drugs not in stock
    
    # Context and checks
    patient_allergies_checked: list[str] = Field(default=[], sa_column=Column(JSONB))
    patient_current_medications: list[str] = Field(default=[], sa_column=Column(JSONB))
    interaction_warnings: list[str] = Field(default=[], sa_column=Column(JSONB))
    contraindication_alerts: list[str] = Field(default=[], sa_column=Column(JSONB))
    
    # Guidelines and rationale
    ghana_guideline_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    ai_rationale: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Facility context
    facility_ids_checked: Optional[list[str]] = Field(default=None, sa_column=Column(JSONB))
    
    # Outcome tracking
    was_accepted: Optional[bool] = Field(default=None, index=True)  # Did doctor accept suggestions?
    prescription_created_id: Optional[UUID] = Field(default=None, foreign_key="prescriptions.id")
    doctor_feedback: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Metadata
    processing_time_seconds: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(6, 2)))
    rxnav_used: bool = Field(default=False)
    tavily_searches_count: int = Field(default=0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="drug_suggestions")
    doctor: "Doctor" = Relationship(back_populates="drug_suggestions")
    prescription_created: Optional["Prescription"] = Relationship(back_populates="drug_suggestion")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import Patient
    from .doctors import Doctor
    from .prescriptions import Prescription

