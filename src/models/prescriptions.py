"""
Prescription models.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .enums import PrescriptionStatus


class Prescription(SQLModel, table=True):
    """Prescription record"""
    
    __tablename__ = "prescriptions"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    consultation_id: Optional[UUID] = Field(default=None, foreign_key="consultations.id", index=True)
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    doctor_id: UUID = Field(foreign_key="doctors.id", index=True)
    prescription_number: str = Field(max_length=50, unique=True, index=True)
    prescribed_date: date = Field(sa_column=Column(Date, index=True))
    status: str = Field(default="ACTIVE", max_length=20, index=True)  # ACTIVE, FILLED, EXPIRED, CANCELLED
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    consultation: Optional["Consultation"] = Relationship(back_populates="prescriptions")
    patient: "Patient" = Relationship(back_populates="prescriptions")
    doctor: "Doctor" = Relationship(back_populates="prescriptions")
    items: list["PrescriptionItem"] = Relationship(back_populates="prescription")
    drug_orders: list["DrugOrder"] = Relationship(back_populates="prescription")


class PrescriptionItem(SQLModel, table=True):
    """Individual items in a prescription"""
    
    __tablename__ = "prescription_items"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    prescription_id: UUID = Field(foreign_key="prescriptions.id", index=True)
    pharmacy_code_id: UUID = Field(foreign_key="pharmacy_codes.id", index=True)
    quantity: int = Field()
    dosage: str = Field(max_length=100)
    frequency: str = Field(max_length=100)  # e.g., "twice daily", "as needed"
    duration: Optional[str] = Field(default=None, max_length=100)  # e.g., "7 days", "until finished"
    instructions: Optional[str] = Field(default=None, sa_column=Column(Text))
    substitution_allowed: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    prescription: Prescription = Relationship(back_populates="items")
    pharmacy_code: "PharmacyCode" = Relationship(back_populates="prescription_items")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import Patient
    from .doctors import Doctor
    from .appointments import Consultation
    from .reference import PharmacyCode
    from .pharmacy import DrugOrder

