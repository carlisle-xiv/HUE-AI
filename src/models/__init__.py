"""
Models package for the HUE healthcare platform.
Exports all models for easy import and Alembic auto-generation.
"""

from sqlmodel import SQLModel

# Import enums
from .enums import (
    UserType,
    AppointmentType,
    AppointmentStatus,
    PrescriptionStatus,
    DrugOrderStatus,
    InsuranceClaimStatus,
    TransactionStatus,
    MedicalConditionStatus,
    HospitalDepartmentType,
    StaffType,
    BedStatus,
    AdmissionType,
    SurgeryStatus,
    EmergencyTriage,
    EquipmentStatus,
    TestOrderStatus,
)

# Import reference models - MIGRATION 1
from .reference import (
    MedicalCode,
    PharmacyCode,
    MedicalCodeDrugMapping,
    MedicalService,
)

# Import core models - MIGRATION 2 (+ MedicalRecordAccess in migration 10)
from .core import (
    User,
    VideoVerification,
    Wallet,
    PaymentMethod,
    Transaction,
    AuditLog,
    MedicalRecordAccess,  # Has FK to patients - added in migration 10
)

# Import patient models - MIGRATION 3
from .patients import (
    Patient,
    PatientVital,
    PatientHabit,
    PatientCondition,
)

# Import doctor models - MIGRATION 3
from .doctors import (
    Doctor,
    DoctorSchedule,
)

# Import appointment models - MIGRATION 4
from .appointments import (
    Appointment,
    Consultation,
    AIConsultation,
)

# Import prescription models - MIGRATION 5
from .prescriptions import (
    Prescription,
    PrescriptionItem,
)

# Import pharmacy models - MIGRATION 6
from .pharmacy import (
    Pharmacy,
    PharmacyInventory,
    DrugOrder,
    DrugOrderItem,
    DrugBarcode,
    BarcodeScan,
)

# Import insurance models - MIGRATION 7
from .insurance import (
    InsuranceCompany,
    InsurancePlan,
    PatientInsurance,
    InsuranceCoverage,
    InsuranceClaim,
)

# Import hospital models - MIGRATION 8
from .hospitals import (
    Hospital,
    HospitalDepartment,
    HospitalStaff,
    HospitalBed,
    HospitalRoom,
    HospitalEquipment,
    HospitalInventory,
)

# Import hospital operations models - MIGRATION 9
from .hospital_operations import (
    HospitalAdmission,
    Surgery,
    SurgeryTeam,
    EmergencyVisit,
    HospitalLabTest,
    HospitalBill,
    HospitalBillItem,
    HospitalMetric,
    StaffSchedule,
)

# Import test models - MIGRATION 10
from .tests import (
    TestOrder,
    TestResult,
)

# Import multi disease detector models - MIGRATION 11
from .multi_disease_detector import (
    ChatSession,
    ChatMessage,
)

# Export all models - MIGRATION 1-3
__all__ = [
    # Base
    "SQLModel",
    
    # Enums
    "UserType",
    "AppointmentType",
    "AppointmentStatus",
    "PrescriptionStatus",
    "DrugOrderStatus",
    "InsuranceClaimStatus",
    "TransactionStatus",
    "MedicalConditionStatus",
    "HospitalDepartmentType",
    "StaffType",
    "BedStatus",
    "AdmissionType",
    "SurgeryStatus",
    "EmergencyTriage",
    "EquipmentStatus",
    "TestOrderStatus",
    
    # Reference models - MIGRATION 1
    "MedicalCode",
    "PharmacyCode",
    "MedicalCodeDrugMapping",
    "MedicalService",
    
    # Core models - MIGRATION 2
    "User",
    "VideoVerification",
    "Wallet",
    "PaymentMethod",
    "Transaction",
    "AuditLog",
    
    # Patient models - MIGRATION 3
    "Patient",
    "PatientVital",
    "PatientHabit",
    "PatientCondition",
    
    # Doctor models - MIGRATION 3
    "Doctor",
    "DoctorSchedule",
    
    # Appointment models - MIGRATION 4
    "Appointment",
    "Consultation",
    "AIConsultation",
    
    # Prescription models - MIGRATION 5
    "Prescription",
    "PrescriptionItem",
    
    # Pharmacy models - MIGRATION 6
    "Pharmacy",
    "PharmacyInventory",
    "DrugOrder",
    "DrugOrderItem",
    "DrugBarcode",
    "BarcodeScan",
    
    # Insurance models - MIGRATION 7
    "InsuranceCompany",
    "InsurancePlan",
    "PatientInsurance",
    "InsuranceCoverage",
    "InsuranceClaim",
    
    # Hospital models - MIGRATION 8
    "Hospital",
    "HospitalDepartment",
    "HospitalStaff",
    "HospitalBed",
    "HospitalRoom",
    "HospitalEquipment",
    "HospitalInventory",
    
    # Hospital operations - MIGRATION 9
    "HospitalAdmission",
    "Surgery",
    "SurgeryTeam",
    "EmergencyVisit",
    "HospitalLabTest",
    "HospitalBill",
    "HospitalBillItem",
    "HospitalMetric",
    "StaffSchedule",
    
    # Test models - MIGRATION 10
    "TestOrder",
    "TestResult",
    
    # MedicalRecordAccess - MIGRATION 10
    "MedicalRecordAccess",
    
    # Multi Disease Detector - MIGRATION 11
    "ChatSession",
    "ChatMessage",
]

