"""
Insurance-related models including companies, plans, coverage, and claims.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Boolean, DECIMAL, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import InsuranceClaimStatus


class InsuranceCompany(SQLModel, table=True):
    """Insurance company profile"""
    
    __tablename__ = "insurance_companies"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    company_name: str = Field(max_length=255, index=True)
    license_number: str = Field(max_length=100, unique=True, index=True)
    address: dict = Field(sa_column=Column(JSONB))
    phone_number: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    website_url: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="insurance_company")
    insurance_plans: list["InsurancePlan"] = Relationship(back_populates="insurance_company")


class InsurancePlan(SQLModel, table=True):
    """Insurance plan details"""
    
    __tablename__ = "insurance_plans"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    insurance_company_id: UUID = Field(foreign_key="insurance_companies.id", index=True)
    plan_name: str = Field(max_length=255, index=True)
    plan_type: Optional[str] = Field(default=None, max_length=50, index=True)  # HMO, PPO, EPO, POS
    coverage_details: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    monthly_premium: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    deductible_amount: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    max_coverage_amount: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    insurance_company: InsuranceCompany = Relationship(back_populates="insurance_plans")
    patient_insurance: list["PatientInsurance"] = Relationship(back_populates="insurance_plan")
    insurance_coverage: list["InsuranceCoverage"] = Relationship(back_populates="insurance_plan")


class PatientInsurance(SQLModel, table=True):
    """Patient's insurance enrollment"""
    
    __tablename__ = "patient_insurance"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    insurance_plan_id: UUID = Field(foreign_key="insurance_plans.id", index=True)
    policy_number: str = Field(max_length=100, unique=True, index=True)
    group_number: Optional[str] = Field(default=None, max_length=100)
    enrollment_date: date = Field(sa_column=Column(Date))
    expiry_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="patient_insurance")
    insurance_plan: InsurancePlan = Relationship(back_populates="patient_insurance")
    insurance_claims: list["InsuranceClaim"] = Relationship(back_populates="patient_insurance")


class InsuranceCoverage(SQLModel, table=True):
    """Coverage details for specific items"""
    
    __tablename__ = "insurance_coverage"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    insurance_plan_id: UUID = Field(foreign_key="insurance_plans.id", index=True)
    coverage_type: str = Field(max_length=20, index=True)  # DRUG, CONSULTATION, TEST, PROCEDURE
    item_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True), index=True))
    coverage_percentage: Decimal = Field(sa_column=Column(DECIMAL(5, 2)))
    max_coverage_amount: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    copay_amount: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    requires_preauth: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    insurance_plan: InsurancePlan = Relationship(back_populates="insurance_coverage")


class InsuranceClaim(SQLModel, table=True):
    """Insurance claim submissions"""
    
    __tablename__ = "insurance_claims"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_insurance_id: UUID = Field(foreign_key="patient_insurance.id", index=True)
    claim_number: str = Field(max_length=50, unique=True, index=True)
    claim_type: str = Field(max_length=20, index=True)  # DRUG, CONSULTATION, TEST, PROCEDURE
    related_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True)))
    total_amount: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    claimed_amount: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    approved_amount: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(10, 2)))
    status: str = Field(default="SUBMITTED", max_length=20, index=True)  # SUBMITTED, UNDER_REVIEW, APPROVED, PARTIALLY_APPROVED, DENIED
    submitted_date: date = Field(sa_column=Column(Date, index=True))
    processed_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    denial_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient_insurance: PatientInsurance = Relationship(back_populates="insurance_claims")
    hospital_bills: list["HospitalBill"] = Relationship(back_populates="insurance_claim")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import User
    from .patients import Patient
    from .hospital_operations import HospitalBill

