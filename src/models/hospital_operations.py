"""
Hospital operations models including admissions, surgeries, emergency visits, billing, and metrics.
"""

from datetime import datetime, date, time
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Time, Integer, Boolean, DECIMAL, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import (
    AdmissionType, SurgeryStatus, EmergencyTriage
)


class HospitalAdmission(SQLModel, table=True):
    """Hospital admission records"""
    
    __tablename__ = "hospital_admissions"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    admitting_doctor_id: UUID = Field(foreign_key="doctors.id", index=True)
    department_id: UUID = Field(foreign_key="hospital_departments.id", index=True)
    admission_number: str = Field(max_length=50, unique=True, index=True)
    admission_type: str = Field(max_length=20)  # EMERGENCY, ELECTIVE, TRANSFER, OBSERVATION
    admission_datetime: datetime = Field(index=True)
    discharge_datetime: Optional[datetime] = Field(default=None)
    estimated_discharge_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    admission_reason: str = Field(sa_column=Column(Text))
    admission_diagnosis: Optional[str] = Field(default=None, sa_column=Column(Text))
    discharge_diagnosis: Optional[str] = Field(default=None, sa_column=Column(Text))
    discharge_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    discharge_instructions: Optional[str] = Field(default=None, sa_column=Column(Text))
    admission_status: str = Field(default="ACTIVE", max_length=20, index=True)  # ACTIVE, DISCHARGED, TRANSFERRED, DECEASED
    discharge_type: Optional[str] = Field(default=None, max_length=20)  # HOME, TRANSFER, AMA, EXPIRED
    total_cost: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(12, 2)))
    insurance_coverage_amount: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(12, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="hospital_admissions")
    hospital: "Hospital" = Relationship(back_populates="admissions")
    admitting_doctor: "Doctor" = Relationship(back_populates="hospital_admissions")
    department: "HospitalDepartment" = Relationship(back_populates="admissions")
    beds: list["HospitalBed"] = Relationship(back_populates="admission")
    bills: list["HospitalBill"] = Relationship(back_populates="admission")


class Surgery(SQLModel, table=True):
    """Surgery records"""
    
    __tablename__ = "surgeries"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    primary_surgeon_id: UUID = Field(foreign_key="doctors.id", index=True)
    anesthesiologist_id: Optional[UUID] = Field(default=None, foreign_key="doctors.id")
    surgery_type: str = Field(max_length=255)
    procedure_codes: Optional[str] = Field(default=None, max_length=255)  # CPT codes
    scheduled_datetime: datetime = Field(index=True)
    estimated_duration_minutes: int = Field()
    actual_start_time: Optional[datetime] = Field(default=None)
    actual_end_time: Optional[datetime] = Field(default=None)
    operating_room_id: Optional[UUID] = Field(default=None, foreign_key="hospital_rooms.id", index=True)
    surgery_status: str = Field(default="SCHEDULED", max_length=20, index=True)  # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, POSTPONED
    pre_op_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    surgical_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    post_op_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    complications: Optional[str] = Field(default=None, sa_column=Column(Text))
    estimated_cost: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    actual_cost: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="surgeries")
    hospital: "Hospital" = Relationship(back_populates="surgeries")
    primary_surgeon: "Doctor" = Relationship(
        back_populates="primary_surgeries",
        sa_relationship_kwargs={"foreign_keys": "[Surgery.primary_surgeon_id]"}
    )
    anesthesiologist: Optional["Doctor"] = Relationship(
        back_populates="anesthesiologist_surgeries",
        sa_relationship_kwargs={"foreign_keys": "[Surgery.anesthesiologist_id]"}
    )
    operating_room: Optional["HospitalRoom"] = Relationship(back_populates="surgeries_as_operating_room")
    surgery_team: list["SurgeryTeam"] = Relationship(back_populates="surgery")


class SurgeryTeam(SQLModel, table=True):
    """Surgery team members"""
    
    __tablename__ = "surgery_team"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    surgery_id: UUID = Field(foreign_key="surgeries.id", index=True)
    staff_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True), index=True))
    staff_type: str = Field(max_length=20)  # SURGEON, ANESTHESIOLOGIST, NURSE, TECHNICIAN
    role: Optional[str] = Field(default=None, max_length=100)  # Primary Surgeon, Assistant Surgeon, Scrub Nurse, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    surgery: Surgery = Relationship(back_populates="surgery_team")


class EmergencyVisit(SQLModel, table=True):
    """Emergency department visit records"""
    
    __tablename__ = "emergency_visits"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    arrival_datetime: datetime = Field(index=True)
    departure_datetime: Optional[datetime] = Field(default=None)
    triage_level: Optional[int] = Field(default=None, index=True)  # 1=Critical, 2=Emergent, 3=Urgent, 4=Less Urgent, 5=Non-urgent
    chief_complaint: str = Field(sa_column=Column(Text))
    vital_signs: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    attending_doctor_id: Optional[UUID] = Field(default=None, foreign_key="doctors.id", index=True)
    triage_nurse_id: Optional[UUID] = Field(default=None, foreign_key="hospital_staff.id")
    visit_status: str = Field(default="WAITING", max_length=20, index=True)  # WAITING, IN_TREATMENT, ADMITTED, DISCHARGED, LEFT_AMA
    disposition: Optional[str] = Field(default=None, max_length=50)  # DISCHARGED_HOME, ADMITTED, TRANSFERRED, DECEASED, LEFT_AMA
    wait_time_minutes: Optional[int] = Field(default=None)
    treatment_time_minutes: Optional[int] = Field(default=None)
    total_cost: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="emergency_visits")
    hospital: "Hospital" = Relationship(back_populates="emergency_visits")
    attending_doctor: Optional["Doctor"] = Relationship(back_populates="emergency_visits")
    triage_nurse: Optional["HospitalStaff"] = Relationship(back_populates="triage_emergency_visits")


class HospitalLabTest(SQLModel, table=True):
    """Hospital laboratory test records"""
    
    __tablename__ = "hospital_lab_tests"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    ordering_doctor_id: UUID = Field(foreign_key="doctors.id", index=True)
    test_name: str = Field(max_length=255)
    test_category: Optional[str] = Field(default=None, max_length=100, index=True)  # BLOOD, URINE, IMAGING, PATHOLOGY, MICROBIOLOGY
    specimen_type: Optional[str] = Field(default=None, max_length=50)
    collection_datetime: Optional[datetime] = Field(default=None, index=True)
    result_datetime: Optional[datetime] = Field(default=None)
    test_status: str = Field(default="ORDERED", max_length=20, index=True)  # ORDERED, COLLECTED, PROCESSING, COMPLETED, CANCELLED
    test_results: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    normal_range: Optional[str] = Field(default=None, max_length=255)
    is_abnormal: bool = Field(default=False)
    technician_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    doctor_interpretation: Optional[str] = Field(default=None, sa_column=Column(Text))
    report_url: Optional[str] = Field(default=None, max_length=500)
    cost: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="hospital_lab_tests")
    hospital: "Hospital" = Relationship(back_populates="lab_tests")
    ordering_doctor: "Doctor" = Relationship(back_populates="hospital_lab_tests")


class HospitalBill(SQLModel, table=True):
    """Hospital billing records"""
    
    __tablename__ = "hospital_bills"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    admission_id: Optional[UUID] = Field(default=None, foreign_key="hospital_admissions.id", index=True)
    bill_number: str = Field(max_length=50, unique=True, index=True)
    bill_type: Optional[str] = Field(default=None, max_length=20)  # ADMISSION, OUTPATIENT, SURGERY, EMERGENCY, CONSULTATION
    bill_date: date = Field(sa_column=Column(Date, index=True))
    due_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    subtotal_amount: Decimal = Field(sa_column=Column(DECIMAL(12, 2)))
    tax_amount: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(12, 2)))
    discount_amount: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(12, 2)))
    total_amount: Decimal = Field(sa_column=Column(DECIMAL(12, 2)))
    paid_amount: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(12, 2)))
    outstanding_amount: Decimal = Field(sa_column=Column(DECIMAL(12, 2)))
    payment_status: str = Field(default="PENDING", max_length=20, index=True)  # PENDING, PARTIAL, PAID, OVERDUE, WRITTEN_OFF
    insurance_claim_id: Optional[UUID] = Field(default=None, foreign_key="insurance_claims.id")
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="hospital_bills")
    hospital: "Hospital" = Relationship(back_populates="bills")
    admission: Optional[HospitalAdmission] = Relationship(back_populates="bills")
    insurance_claim: Optional["InsuranceClaim"] = Relationship(back_populates="hospital_bills")
    bill_items: list["HospitalBillItem"] = Relationship(back_populates="hospital_bill")


class HospitalBillItem(SQLModel, table=True):
    """Individual items in hospital bills"""
    
    __tablename__ = "hospital_bill_items"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    hospital_bill_id: UUID = Field(foreign_key="hospital_bills.id", index=True)
    item_type: Optional[str] = Field(default=None, max_length=50, index=True)  # ROOM_CHARGE, DOCTOR_FEE, MEDICATION, PROCEDURE, EQUIPMENT_USE
    item_description: str = Field(max_length=500)
    item_code: Optional[str] = Field(default=None, max_length=50)
    quantity: int = Field(default=1)
    unit_price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    total_price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    service_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    provider_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True), index=True))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital_bill: HospitalBill = Relationship(back_populates="bill_items")


class HospitalMetric(SQLModel, table=True):
    """Hospital performance metrics"""
    
    __tablename__ = "hospital_metrics"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    metric_date: date = Field(sa_column=Column(Date, index=True))
    bed_occupancy_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    average_length_of_stay: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(4, 1)))
    emergency_wait_time_avg: Optional[int] = Field(default=None)  # Minutes
    patient_satisfaction_score: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(3, 2)))
    readmission_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    infection_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    mortality_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    staff_to_patient_ratio: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(4, 2)))
    revenue: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(12, 2)))
    operating_expenses: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(12, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital: "Hospital" = Relationship(back_populates="metrics")


class StaffSchedule(SQLModel, table=True):
    """Staff scheduling"""
    
    __tablename__ = "staff_schedules"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    staff_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True), index=True))
    staff_type: str = Field(max_length=20)  # DOCTOR, NURSE, TECHNICIAN, ADMIN
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    department_id: Optional[UUID] = Field(default=None, foreign_key="hospital_departments.id", index=True)
    shift_date: date = Field(sa_column=Column(Date, index=True))
    shift_start_time: time = Field(sa_column=Column(Time))
    shift_end_time: time = Field(sa_column=Column(Time))
    shift_type: Optional[str] = Field(default=None, max_length=20)  # DAY, NIGHT, EVENING, ON_CALL
    is_overtime: bool = Field(default=False)
    actual_clock_in: Optional[datetime] = Field(default=None)
    actual_clock_out: Optional[datetime] = Field(default=None)
    break_duration_minutes: int = Field(default=30)
    status: str = Field(default="SCHEDULED", max_length=20)  # SCHEDULED, WORKING, COMPLETED, ABSENT, SICK_LEAVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital: "Hospital" = Relationship(back_populates="staff_schedules")
    department: Optional["HospitalDepartment"] = Relationship(back_populates="staff_schedules")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import Patient
    from .doctors import Doctor
    from .hospitals import Hospital, HospitalDepartment, HospitalBed, HospitalRoom, HospitalStaff
    from .insurance import InsuranceClaim

