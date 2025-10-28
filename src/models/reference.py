"""
Reference data models for medical codes, pharmacy codes, and medical services.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Boolean, Integer, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class MedicalCode(SQLModel, table=True):
    """Medical codes (ICD-10, SNOMED CT, or custom codes)"""
    
    __tablename__ = "medical_codes"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    code: str = Field(max_length=50, unique=True, index=True)
    code_type: str = Field(max_length=20)  # ICD10, SNOMED, CUSTOM
    condition_name: str = Field(max_length=255, index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    category: Optional[str] = Field(default=None, max_length=100)
    severity_level: Optional[str] = Field(default=None, max_length=20)  # LOW, MEDIUM, HIGH, CRITICAL
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    drug_mappings: list["MedicalCodeDrugMapping"] = Relationship(back_populates="medical_code")
    patient_conditions: list["PatientCondition"] = Relationship(back_populates="medical_code")


class PharmacyCode(SQLModel, table=True):
    """Pharmacy drug codes (NDC, RxNorm, or custom codes)"""
    
    __tablename__ = "pharmacy_codes"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    drug_code: str = Field(max_length=50, unique=True, index=True)
    drug_name: str = Field(max_length=255, index=True)
    generic_name: Optional[str] = Field(default=None, max_length=255, index=True)
    brand_names: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    dosage_form: Optional[str] = Field(default=None, max_length=100)  # tablet, capsule, injection, etc.
    strength: Optional[str] = Field(default=None, max_length=100)  # e.g., 500mg, 10mg/ml
    therapeutic_class: Optional[str] = Field(default=None, max_length=100, index=True)
    contraindications: Optional[str] = Field(default=None, sa_column=Column(Text))
    side_effects: Optional[str] = Field(default=None, sa_column=Column(Text))
    fda_approved: bool = Field(default=False, index=True)
    prescription_required: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    drug_mappings: list["MedicalCodeDrugMapping"] = Relationship(back_populates="pharmacy_code")
    prescription_items: list["PrescriptionItem"] = Relationship(back_populates="pharmacy_code")
    pharmacy_inventory: list["PharmacyInventory"] = Relationship(back_populates="pharmacy_code")
    drug_barcodes: list["DrugBarcode"] = Relationship(back_populates="pharmacy_code")


class MedicalCodeDrugMapping(SQLModel, table=True):
    """Mapping between medical conditions and recommended drugs"""
    
    __tablename__ = "medical_code_drug_mapping"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    medical_code_id: UUID = Field(foreign_key="medical_codes.id", index=True)
    pharmacy_code_id: UUID = Field(foreign_key="pharmacy_codes.id", index=True)
    effectiveness_rating: Optional[int] = Field(default=None)  # 1-10 scale
    is_first_line_treatment: bool = Field(default=False)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    medical_code: MedicalCode = Relationship(back_populates="drug_mappings")
    pharmacy_code: PharmacyCode = Relationship(back_populates="drug_mappings")


class MedicalService(SQLModel, table=True):
    """Medical services including tests, imaging, procedures"""
    
    __tablename__ = "medical_services"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    service_name: str = Field(max_length=255, index=True)
    service_type: str = Field(max_length=50, index=True)  # DNA_TEST, GENOTYPE_TEST, LAB_TEST, IMAGING, etc.
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    base_price: float = Field()
    sample_required: Optional[str] = Field(default=None, max_length=100)  # blood, saliva, urine, etc.
    turnaround_time_days: Optional[int] = Field(default=None)
    requires_fasting: bool = Field(default=False)
    special_instructions: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    test_orders: list["TestOrder"] = Relationship(back_populates="medical_service")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import PatientCondition
    from .prescriptions import PrescriptionItem
    from .pharmacy import PharmacyInventory, DrugBarcode
    from .tests import TestOrder

