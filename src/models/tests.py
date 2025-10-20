"""
Medical test models including test orders and results.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, DECIMAL, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import TestOrderStatus


class TestOrder(SQLModel, table=True):
    """Medical test order"""
    
    __tablename__ = "test_orders"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    doctor_id: Optional[UUID] = Field(default=None, foreign_key="doctors.id", index=True)
    hospital_id: Optional[UUID] = Field(default=None, foreign_key="hospitals.id", index=True)
    medical_service_id: UUID = Field(foreign_key="medical_services.id", index=True)
    order_number: str = Field(max_length=50, unique=True, index=True)
    order_type: str = Field(max_length=20)  # INDIVIDUAL, GROUP, BULK
    total_amount: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    status: str = Field(default="ORDERED", max_length=20, index=True)  # ORDERED, SAMPLE_COLLECTED, PROCESSING, COMPLETED, CANCELLED
    scheduled_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    sample_collection_method: Optional[str] = Field(default=None, max_length=20)  # HOME_VISIT, CLINIC_VISIT, SELF_COLLECTION
    billing_entity: Optional[str] = Field(default=None, max_length=20)  # PATIENT, HOSPITAL, INSURANCE
    billing_entity_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True)))
    special_instructions: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="test_orders")
    doctor: Optional["Doctor"] = Relationship(back_populates="test_orders")
    hospital: Optional["Hospital"] = Relationship(back_populates="test_orders")
    medical_service: "MedicalService" = Relationship(back_populates="test_orders")
    test_result: Optional["TestResult"] = Relationship(back_populates="test_order")


class TestResult(SQLModel, table=True):
    """Medical test results"""
    
    __tablename__ = "test_results"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    test_order_id: UUID = Field(foreign_key="test_orders.id", unique=True, index=True)
    result_data: dict = Field(sa_column=Column(JSONB))
    interpretation: Optional[str] = Field(default=None, sa_column=Column(Text))
    normal_ranges: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    abnormal_flags: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    reviewed_by_id: Optional[UUID] = Field(default=None, foreign_key="doctors.id", index=True)
    reviewed_at: Optional[datetime] = Field(default=None)
    report_file_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    test_order: TestOrder = Relationship(back_populates="test_result")
    reviewed_by: Optional["Doctor"] = Relationship(back_populates="reviewed_test_results")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import Patient
    from .doctors import Doctor
    from .hospitals import Hospital
    from .reference import MedicalService

