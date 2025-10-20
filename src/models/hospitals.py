"""
Hospital infrastructure models including hospitals, departments, staff, beds, rooms, and equipment.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Integer, Boolean, DECIMAL, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import (
    HospitalDepartmentType, StaffType, BedStatus,
    EquipmentStatus
)


class Hospital(SQLModel, table=True):
    """Hospital profile"""
    
    __tablename__ = "hospitals"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    name: str = Field(max_length=255, index=True)
    license_number: str = Field(max_length=100, unique=True, index=True)
    hospital_type: Optional[str] = Field(default=None, max_length=50, index=True)  # HOSPITAL, CLINIC, SPECIALTY_CENTER
    address: dict = Field(sa_column=Column(JSONB))
    phone_number: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    operating_hours: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    services_offered: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    accreditation: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="hospital")
    doctors: list["Doctor"] = Relationship(back_populates="hospital")
    departments: list["HospitalDepartment"] = Relationship(back_populates="hospital")
    staff: list["HospitalStaff"] = Relationship(back_populates="hospital")
    beds: list["HospitalBed"] = Relationship(back_populates="hospital")
    rooms: list["HospitalRoom"] = Relationship(back_populates="hospital")
    equipment: list["HospitalEquipment"] = Relationship(back_populates="hospital")
    inventory: list["HospitalInventory"] = Relationship(back_populates="hospital")
    admissions: list["HospitalAdmission"] = Relationship(back_populates="hospital")
    surgeries: list["Surgery"] = Relationship(back_populates="hospital")
    bills: list["HospitalBill"] = Relationship(back_populates="hospital")
    emergency_visits: list["EmergencyVisit"] = Relationship(back_populates="hospital")
    lab_tests: list["HospitalLabTest"] = Relationship(back_populates="hospital")
    metrics: list["HospitalMetric"] = Relationship(back_populates="hospital")
    staff_schedules: list["StaffSchedule"] = Relationship(back_populates="hospital")
    test_orders: list["TestOrder"] = Relationship(back_populates="hospital")


class HospitalDepartment(SQLModel, table=True):
    """Hospital department"""
    
    __tablename__ = "hospital_departments"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    department_name: str = Field(max_length=255)
    department_type: Optional[str] = Field(default=None, max_length=50, index=True)
    head_doctor_id: Optional[UUID] = Field(default=None, foreign_key="doctors.id", index=True)
    bed_capacity: int = Field(default=0)
    available_beds: int = Field(default=0)
    location: Optional[str] = Field(default=None, max_length=255)
    operating_hours: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    specialized_equipment: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital: Hospital = Relationship(back_populates="departments")
    head_doctor: Optional["Doctor"] = Relationship(back_populates="headed_departments")
    staff: list["HospitalStaff"] = Relationship(back_populates="department")
    beds: list["HospitalBed"] = Relationship(back_populates="department")
    rooms: list["HospitalRoom"] = Relationship(back_populates="department")
    equipment: list["HospitalEquipment"] = Relationship(back_populates="department")
    inventory: list["HospitalInventory"] = Relationship(back_populates="department")
    admissions: list["HospitalAdmission"] = Relationship(back_populates="department")
    staff_schedules: list["StaffSchedule"] = Relationship(back_populates="department")


class HospitalStaff(SQLModel, table=True):
    """Hospital staff members"""
    
    __tablename__ = "hospital_staff"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    department_id: Optional[UUID] = Field(default=None, foreign_key="hospital_departments.id", index=True)
    staff_type: str = Field(max_length=50, index=True)
    employee_id: str = Field(max_length=50)
    legal_name: str = Field(max_length=255)
    position_title: Optional[str] = Field(default=None, max_length=255)
    license_number: Optional[str] = Field(default=None, max_length=100)
    qualifications: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    hire_date: date = Field(sa_column=Column(Date))
    employment_status: str = Field(default="ACTIVE", max_length=20, index=True)  # ACTIVE, ON_LEAVE, TERMINATED, RETIRED
    shift_pattern: Optional[str] = Field(default=None, max_length=50)  # DAY, NIGHT, ROTATING, PART_TIME
    hourly_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 2)))
    emergency_contact: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="hospital_staff")
    hospital: Hospital = Relationship(back_populates="staff")
    department: Optional[HospitalDepartment] = Relationship(back_populates="staff")
    triage_emergency_visits: list["EmergencyVisit"] = Relationship(back_populates="triage_nurse")


class HospitalBed(SQLModel, table=True):
    """Hospital bed management"""
    
    __tablename__ = "hospital_beds"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    department_id: UUID = Field(foreign_key="hospital_departments.id", index=True)
    bed_number: str = Field(max_length=20)
    bed_type: Optional[str] = Field(default=None, max_length=50)  # ICU, GENERAL, PRIVATE, MATERNITY, PEDIATRIC
    room_number: Optional[str] = Field(default=None, max_length=20)
    floor_number: Optional[str] = Field(default=None, max_length=10)
    bed_status: str = Field(default="AVAILABLE", max_length=20, index=True)
    patient_id: Optional[UUID] = Field(default=None, foreign_key="patients.id", index=True)
    admission_id: Optional[UUID] = Field(default=None, foreign_key="hospital_admissions.id", index=True)
    daily_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 2)))
    equipment: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    last_cleaned: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital: Hospital = Relationship(back_populates="beds")
    department: HospitalDepartment = Relationship(back_populates="beds")
    patient: Optional["Patient"] = Relationship(back_populates="hospital_beds")
    admission: Optional["HospitalAdmission"] = Relationship(back_populates="beds")


class HospitalRoom(SQLModel, table=True):
    """Hospital room management"""
    
    __tablename__ = "hospital_rooms"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    department_id: UUID = Field(foreign_key="hospital_departments.id", index=True)
    room_number: str = Field(max_length=20)
    room_type: Optional[str] = Field(default=None, max_length=50, index=True)  # PATIENT_ROOM, OPERATING_ROOM, ICU, CONSULTATION, LABORATORY
    floor_number: Optional[str] = Field(default=None, max_length=10)
    bed_count: int = Field(default=1)
    room_status: str = Field(default="AVAILABLE", max_length=20, index=True)  # AVAILABLE, OCCUPIED, CLEANING, MAINTENANCE
    daily_rate: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 2)))
    amenities: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    equipment_ids: Optional[list[UUID]] = Field(default=None, sa_column=Column(ARRAY(PGUUID(as_uuid=True))))
    accessibility_features: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital: Hospital = Relationship(back_populates="rooms")
    department: HospitalDepartment = Relationship(back_populates="rooms")
    surgeries_as_operating_room: list["Surgery"] = Relationship(back_populates="operating_room")


class HospitalEquipment(SQLModel, table=True):
    """Hospital equipment tracking"""
    
    __tablename__ = "hospital_equipment"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    department_id: Optional[UUID] = Field(default=None, foreign_key="hospital_departments.id", index=True)
    equipment_name: str = Field(max_length=255)
    equipment_type: Optional[str] = Field(default=None, max_length=100, index=True)  # MRI, CT_SCAN, X_RAY, VENTILATOR, MONITOR, etc.
    model_number: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100, unique=True, index=True)
    manufacturer: Optional[str] = Field(default=None, max_length=255)
    purchase_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    warranty_expiry: Optional[date] = Field(default=None, sa_column=Column(Date))
    last_maintenance_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    next_maintenance_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    equipment_status: str = Field(default="OPERATIONAL", max_length=20, index=True)
    location: Optional[str] = Field(default=None, max_length=255)
    cost_per_use: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 2)))
    maintenance_cost: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    is_portable: bool = Field(default=False)
    requires_specialist: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital: Hospital = Relationship(back_populates="equipment")
    department: Optional[HospitalDepartment] = Relationship(back_populates="equipment")


class HospitalInventory(SQLModel, table=True):
    """Hospital inventory management"""
    
    __tablename__ = "hospital_inventory"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True)
    department_id: Optional[UUID] = Field(default=None, foreign_key="hospital_departments.id", index=True)
    item_name: str = Field(max_length=255)
    item_category: Optional[str] = Field(default=None, max_length=100, index=True)  # MEDICAL_SUPPLIES, PHARMACEUTICALS, EQUIPMENT, FOOD, LINEN
    item_code: Optional[str] = Field(default=None, max_length=50, unique=True, index=True)
    supplier: Optional[str] = Field(default=None, max_length=255)
    unit_of_measure: Optional[str] = Field(default=None, max_length=20)  # pieces, boxes, liters, kg
    current_stock: int = Field(default=0, index=True)
    minimum_stock_level: int = Field(default=10)
    maximum_stock_level: Optional[int] = Field(default=None)
    unit_cost: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(8, 2)))
    expiry_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    batch_number: Optional[str] = Field(default=None, max_length=100)
    storage_location: Optional[str] = Field(default=None, max_length=255)
    last_restocked_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    hospital: Hospital = Relationship(back_populates="inventory")
    department: Optional[HospitalDepartment] = Relationship(back_populates="inventory")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import User
    from .patients import Patient
    from .doctors import Doctor
    from .tests import TestOrder
    from .hospital_operations import (
        HospitalAdmission, Surgery, HospitalBill, EmergencyVisit,
        HospitalLabTest, HospitalMetric, StaffSchedule
    )

