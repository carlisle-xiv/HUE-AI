"""
Appointment and consultation models.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Integer, Boolean, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import AppointmentType, AppointmentStatus


class Appointment(SQLModel, table=True):
    """Appointment between patient and doctor"""
    
    __tablename__ = "appointments"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    doctor_id: UUID = Field(foreign_key="doctors.id", index=True)
    appointment_datetime: datetime = Field(index=True)
    duration_minutes: int = Field(default=30)
    buffer_minutes: int = Field(default=15)
    appointment_type: str = Field(max_length=20)  # VIDEO, AUDIO, CHAT, IN_PERSON
    status: str = Field(default="SCHEDULED", max_length=20, index=True)  # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW
    chief_complaint: Optional[str] = Field(default=None, sa_column=Column(Text))
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="appointments")
    doctor: "Doctor" = Relationship(back_populates="appointments")
    consultation: Optional["Consultation"] = Relationship(back_populates="appointment")


class Consultation(SQLModel, table=True):
    """Medical consultation record"""
    
    __tablename__ = "consultations"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    appointment_id: UUID = Field(foreign_key="appointments.id", unique=True, index=True)
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    doctor_id: UUID = Field(foreign_key="doctors.id", index=True)
    consultation_type: str = Field(max_length=20)  # VIDEO, AUDIO, CHAT, IN_PERSON
    start_time: datetime = Field(index=True)
    end_time: Optional[datetime] = Field(default=None)
    chief_complaint: Optional[str] = Field(default=None, sa_column=Column(Text))
    history_of_present_illness: Optional[str] = Field(default=None, sa_column=Column(Text))
    assessment: Optional[str] = Field(default=None, sa_column=Column(Text))
    diagnosis_codes: Optional[list[UUID]] = Field(default=None, sa_column=Column(ARRAY(PGUUID(as_uuid=True))))
    treatment_plan: Optional[str] = Field(default=None, sa_column=Column(Text))
    doctor_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    patient_feedback: Optional[str] = Field(default=None, sa_column=Column(Text))
    consultation_rating: Optional[int] = Field(default=None)  # 1-5 rating by patient
    is_completed: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    appointment: Appointment = Relationship(back_populates="consultation")
    patient: "Patient" = Relationship(back_populates="consultations")
    doctor: "Doctor" = Relationship(back_populates="consultations")
    prescriptions: list["Prescription"] = Relationship(back_populates="consultation")


class AIConsultation(SQLModel, table=True):
    """AI-powered consultation record"""
    
    __tablename__ = "ai_consultations"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    session_id: UUID = Field(sa_column=Column(PGUUID(as_uuid=True), index=True))
    symptoms_described: str = Field(sa_column=Column(Text))
    ai_suggested_conditions: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    ai_recommendations: Optional[str] = Field(default=None, sa_column=Column(Text))
    risk_assessment: Optional[str] = Field(default=None, max_length=20, index=True)  # LOW, MEDIUM, HIGH, EMERGENCY
    should_see_doctor: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="ai_consultations")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import Patient
    from .doctors import Doctor
    from .prescriptions import Prescription

