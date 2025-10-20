"""
Enums for the HUE healthcare platform.
All enums correspond to PostgreSQL ENUM types.
"""

from enum import Enum


class UserType(str, Enum):
    """User type enumeration"""
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    PHARMACY = "PHARMACY"
    INSURANCE = "INSURANCE"
    HOSPITAL = "HOSPITAL"
    ADMIN = "ADMIN"


class AppointmentType(str, Enum):
    """Appointment type enumeration"""
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    CHAT = "CHAT"
    IN_PERSON = "IN_PERSON"


class AppointmentStatus(str, Enum):
    """Appointment status enumeration"""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class PrescriptionStatus(str, Enum):
    """Prescription status enumeration"""
    ACTIVE = "ACTIVE"
    FILLED = "FILLED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class DrugOrderStatus(str, Enum):
    """Drug order status enumeration"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PREPARED = "PREPARED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"


class InsuranceClaimStatus(str, Enum):
    """Insurance claim status enumeration"""
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    DENIED = "DENIED"


class TransactionStatus(str, Enum):
    """Transaction status enumeration"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MedicalConditionStatus(str, Enum):
    """Medical condition status enumeration"""
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    CHRONIC = "CHRONIC"
    REMISSION = "REMISSION"


class HospitalDepartmentType(str, Enum):
    """Hospital department type enumeration"""
    EMERGENCY = "EMERGENCY"
    ICU = "ICU"
    SURGERY = "SURGERY"
    CARDIOLOGY = "CARDIOLOGY"
    PEDIATRICS = "PEDIATRICS"
    MATERNITY = "MATERNITY"
    ONCOLOGY = "ONCOLOGY"
    ORTHOPEDICS = "ORTHOPEDICS"
    NEUROLOGY = "NEUROLOGY"
    RADIOLOGY = "RADIOLOGY"
    LABORATORY = "LABORATORY"
    PHARMACY = "PHARMACY"
    ADMINISTRATION = "ADMINISTRATION"


class StaffType(str, Enum):
    """Staff type enumeration"""
    NURSE = "NURSE"
    TECHNICIAN = "TECHNICIAN"
    ADMIN = "ADMIN"
    RECEPTIONIST = "RECEPTIONIST"
    SECURITY = "SECURITY"
    JANITOR = "JANITOR"
    LABORATORY_TECHNICIAN = "LABORATORY_TECHNICIAN"
    RADIOLOGIC_TECHNOLOGIST = "RADIOLOGIC_TECHNOLOGIST"
    PHARMACIST = "PHARMACIST"


class BedStatus(str, Enum):
    """Bed status enumeration"""
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    RESERVED = "RESERVED"


class AdmissionType(str, Enum):
    """Admission type enumeration"""
    EMERGENCY = "EMERGENCY"
    ELECTIVE = "ELECTIVE"
    TRANSFER = "TRANSFER"
    OBSERVATION = "OBSERVATION"
    OUTPATIENT = "OUTPATIENT"


class SurgeryStatus(str, Enum):
    """Surgery status enumeration"""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"


class EmergencyTriage(str, Enum):
    """Emergency triage enumeration"""
    CRITICAL = "CRITICAL"
    EMERGENT = "EMERGENT"
    URGENT = "URGENT"
    LESS_URGENT = "LESS_URGENT"
    NON_URGENT = "NON_URGENT"


class EquipmentStatus(str, Enum):
    """Equipment status enumeration"""
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    RETIRED = "RETIRED"
    CALIBRATION_REQUIRED = "CALIBRATION_REQUIRED"


class TestOrderStatus(str, Enum):
    """Test order status enumeration"""
    ORDERED = "ORDERED"
    SAMPLE_COLLECTED = "SAMPLE_COLLECTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

