"""
Doctor-related models including doctor profiles and schedules.
"""

from datetime import datetime, date, time
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Time, Integer, Boolean, DECIMAL, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB


class Doctor(SQLModel, table=True):
    """Doctor profile"""
    
    __tablename__ = "doctors"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    hospital_id: Optional[UUID] = Field(default=None, foreign_key="hospitals.id", index=True)
    legal_name: str = Field(max_length=255)
    preferred_name: Optional[str] = Field(default=None, max_length=255)
    date_of_birth: date = Field(sa_column=Column(Date))
    gender: Optional[str] = Field(default=None, max_length=50)
    profile_image_url: Optional[str] = Field(default=None, max_length=500)
    license_number: str = Field(max_length=100, unique=True, index=True)
    specializations: list[str] = Field(sa_column=Column(ARRAY(String)))
    years_of_practice: Optional[int] = Field(default=None)
    medical_school: Optional[str] = Field(default=None, max_length=255)
    certifications: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    languages: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    bio: Optional[str] = Field(default=None, sa_column=Column(Text))
    consultation_fee: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    rating_average: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(3, 2), index=True))
    total_ratings: int = Field(default=0)
    is_active: bool = Field(default=True)
    available_for_consultation: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="doctor")
    hospital: Optional["Hospital"] = Relationship(back_populates="doctors")
    schedules: list["DoctorSchedule"] = Relationship(back_populates="doctor")
    appointments: list["Appointment"] = Relationship(back_populates="doctor")
    consultations: list["Consultation"] = Relationship(back_populates="doctor")
    prescriptions: list["Prescription"] = Relationship(back_populates="doctor")
    diagnosed_conditions: list["PatientCondition"] = Relationship(back_populates="diagnosed_by")
    test_orders: list["TestOrder"] = Relationship(back_populates="doctor")
    reviewed_test_results: list["TestResult"] = Relationship(back_populates="reviewed_by")
    headed_departments: list["HospitalDepartment"] = Relationship(back_populates="head_doctor")
    hospital_admissions: list["HospitalAdmission"] = Relationship(
        back_populates="admitting_doctor",
        sa_relationship_kwargs={"foreign_keys": "HospitalAdmission.admitting_doctor_id"}
    )
    primary_surgeries: list["Surgery"] = Relationship(
        back_populates="primary_surgeon",
        sa_relationship_kwargs={"foreign_keys": "Surgery.primary_surgeon_id"}
    )
    anesthesiologist_surgeries: list["Surgery"] = Relationship(
        back_populates="anesthesiologist",
        sa_relationship_kwargs={"foreign_keys": "Surgery.anesthesiologist_id"}
    )
    emergency_visits: list["EmergencyVisit"] = Relationship(back_populates="attending_doctor")
    hospital_lab_tests: list["HospitalLabTest"] = Relationship(back_populates="ordering_doctor")


class DoctorSchedule(SQLModel, table=True):
    """Doctor availability schedule"""
    
    __tablename__ = "doctor_schedules"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    doctor_id: UUID = Field(foreign_key="doctors.id", index=True)
    day_of_week: int = Field()  # 0=Sunday, 1=Monday, etc.
    start_time: time = Field(sa_column=Column(Time))
    end_time: time = Field(sa_column=Column(Time))
    is_available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    doctor: Doctor = Relationship(back_populates="schedules")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import User
    from .patients import PatientCondition
    from .appointments import Appointment, Consultation
    from .prescriptions import Prescription
    from .hospitals import Hospital, HospitalDepartment
    from .tests import TestOrder, TestResult
    from .hospital_operations import (
        HospitalAdmission, Surgery, EmergencyVisit, HospitalLabTest
    )

