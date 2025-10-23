"""
Patient-related models including patient profiles, vitals, habits, and conditions.
"""

import datetime as dt
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Text, Date, DECIMAL, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import MedicalConditionStatus


class Patient(SQLModel, table=True):
    """Patient profile"""
    
    __tablename__ = "patients"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    legal_name: str = Field(max_length=255, index=True)
    preferred_name: Optional[str] = Field(default=None, max_length=255)
    date_of_birth: dt.date = Field(sa_column=Column(Date, index=True))
    biological_sex: Optional[str] = Field(default=None, max_length=10)  # MALE, FEMALE, INTERSEX
    gender_identity: Optional[str] = Field(default=None, max_length=50)
    national_id: Optional[str] = Field(default=None, max_length=50, unique=True, index=True)
    profile_image_url: Optional[str] = Field(default=None, max_length=500)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="patient")
    vitals: list["PatientVital"] = Relationship(back_populates="patient")
    habits: list["PatientHabit"] = Relationship(back_populates="patient")
    conditions: list["PatientCondition"] = Relationship(back_populates="patient")
    appointments: list["Appointment"] = Relationship(back_populates="patient")
    consultations: list["Consultation"] = Relationship(back_populates="patient")
    ai_consultations: list["AIConsultation"] = Relationship(back_populates="patient")
    chat_sessions: list["ChatSession"] = Relationship(back_populates="patient")
    prescriptions: list["Prescription"] = Relationship(back_populates="patient")
    drug_orders: list["DrugOrder"] = Relationship(back_populates="patient")
    patient_insurance: list["PatientInsurance"] = Relationship(back_populates="patient")
    test_orders: list["TestOrder"] = Relationship(back_populates="patient")
    medical_record_accesses: list["MedicalRecordAccess"] = Relationship(back_populates="patient")
    hospital_admissions: list["HospitalAdmission"] = Relationship(back_populates="patient")
    hospital_beds: list["HospitalBed"] = Relationship(back_populates="patient")
    surgeries: list["Surgery"] = Relationship(back_populates="patient")
    emergency_visits: list["EmergencyVisit"] = Relationship(back_populates="patient")
    hospital_lab_tests: list["HospitalLabTest"] = Relationship(back_populates="patient")
    hospital_bills: list["HospitalBill"] = Relationship(back_populates="patient")


class PatientVital(SQLModel, table=True):
    """Patient vital signs records"""
    
    __tablename__ = "patient_vitals"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    recorded_at: datetime = Field(index=True)
    blood_type: Optional[str] = Field(default=None, max_length=5)
    blood_pressure_systolic: Optional[int] = Field(default=None)
    blood_pressure_diastolic: Optional[int] = Field(default=None)
    heart_rate_bpm: Optional[int] = Field(default=None)
    temperature_celsius: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(4, 2)))
    respiratory_rate: Optional[int] = Field(default=None)
    oxygen_saturation: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    glucose_level: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(6, 2)))
    weight_kg: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    height_cm: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    bmi: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(4, 2)))
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    recorded_by_type: Optional[str] = Field(default=None, max_length=20)  # PATIENT, DOCTOR, NURSE, DEVICE
    recorded_by_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: Patient = Relationship(back_populates="vitals")


class PatientHabit(SQLModel, table=True):
    """Patient habit tracking"""
    
    __tablename__ = "patient_habits"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    habit_type: str = Field(max_length=50, index=True)  # WATER_INTAKE, SLEEP, EXERCISE, STANDING, MEDICATION_ADHERENCE
    target_value: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    target_unit: Optional[str] = Field(default=None, max_length=20)  # liters, hours, minutes, times
    date: dt.date = Field(sa_column=Column(Date, index=True))
    actual_value: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: Patient = Relationship(back_populates="habits")


class PatientCondition(SQLModel, table=True):
    """Patient medical conditions"""
    
    __tablename__ = "patient_conditions"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    medical_code_id: UUID = Field(foreign_key="medical_codes.id", index=True)
    diagnosed_date: Optional[dt.date] = Field(default=None, sa_column=Column(Date, index=True))
    status: str = Field(default="ACTIVE", max_length=20, index=True)  # ACTIVE, RESOLVED, CHRONIC, REMISSION
    severity: Optional[str] = Field(default=None, max_length=20)  # MILD, MODERATE, SEVERE, CRITICAL
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    diagnosed_by_id: Optional[UUID] = Field(default=None, foreign_key="doctors.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: Patient = Relationship(back_populates="conditions")
    medical_code: "MedicalCode" = Relationship(back_populates="patient_conditions")
    diagnosed_by: Optional["Doctor"] = Relationship(back_populates="diagnosed_conditions")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import User, MedicalRecordAccess
    from .reference import MedicalCode
    from .doctors import Doctor
    from .appointments import Appointment, Consultation, AIConsultation
    from .multi_disease_detector import ChatSession
    from .prescriptions import Prescription
    from .pharmacy import DrugOrder
    from .insurance import PatientInsurance
    from .tests import TestOrder
    from .hospitals import HospitalBed
    from .hospital_operations import (
        HospitalAdmission, Surgery, EmergencyVisit,
        HospitalLabTest, HospitalBill
    )

