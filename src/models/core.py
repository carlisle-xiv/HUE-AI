"""
Core models for users, authentication, payments, and access control.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Boolean, func, DECIMAL
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import UserType


class User(SQLModel, table=True):
    """User account model"""
    
    __tablename__ = "users"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=20, index=True)
    user_type: str = Field(max_length=20, index=True)  # PATIENT, DOCTOR, PHARMACY, INSURANCE, HOSPITAL, ADMIN
    country: str = Field(default="GH", max_length=20)
    is_active: bool = Field(default=True, index=True)
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    # Relationships
    patient: Optional["Patient"] = Relationship(back_populates="user")
    doctor: Optional["Doctor"] = Relationship(back_populates="user")
    hospital: Optional["Hospital"] = Relationship(back_populates="user")
    pharmacy: Optional["Pharmacy"] = Relationship(back_populates="user")
    insurance_company: Optional["InsuranceCompany"] = Relationship(back_populates="user")
    hospital_staff: Optional["HospitalStaff"] = Relationship(back_populates="user")
    video_verifications: list["VideoVerification"] = Relationship(back_populates="user")
    wallet: Optional["Wallet"] = Relationship(back_populates="user")
    payment_methods: list["PaymentMethod"] = Relationship(back_populates="user")
    transactions: list["Transaction"] = Relationship(back_populates="user")
    barcode_scans: list["BarcodeScan"] = Relationship(back_populates="user")
    audit_logs: list["AuditLog"] = Relationship(back_populates="user")
    medical_record_accesses: list["MedicalRecordAccess"] = Relationship(
        back_populates="accessor",
        sa_relationship_kwargs={"foreign_keys": "MedicalRecordAccess.accessor_id"}
    )


class VideoVerification(SQLModel, table=True):
    """Video verification records for user identity verification"""
    
    __tablename__ = "video_verifications"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id")
    selected_date: datetime = Field()
    type: str = Field(max_length=100)  # Zoom, Google meet, Live, etc
    verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="video_verifications")


class Wallet(SQLModel, table=True):
    """User wallet for HUE tokens and cryptocurrency"""
    
    __tablename__ = "wallets"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    balance: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(18, 8)))
    eth_wallet_address: Optional[str] = Field(default=None, max_length=42, unique=True, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="wallet")


class PaymentMethod(SQLModel, table=True):
    """Payment methods for users"""
    
    __tablename__ = "payment_methods"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", index=True)
    method_type: str = Field(max_length=20, index=True)  # CARD, MOBILE_MONEY, BANK_TRANSFER, HUE_TOKEN
    provider: Optional[str] = Field(default=None, max_length=50)  # VISA, MASTERCARD, MTN, VODAFONE, etc.
    encrypted_details: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    is_default: bool = Field(default=False, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="payment_methods")
    transactions: list["Transaction"] = Relationship(back_populates="payment_method")


class Transaction(SQLModel, table=True):
    """Financial transactions"""
    
    __tablename__ = "transactions"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", index=True)
    transaction_type: str = Field(max_length=20, index=True)  # PAYMENT, REFUND, DEPOSIT, WITHDRAWAL, TRANSFER
    amount: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    currency: str = Field(default="HUE", max_length=10)
    payment_method_id: Optional[UUID] = Field(default=None, foreign_key="payment_methods.id")
    related_type: Optional[str] = Field(default=None, max_length=20)  # DRUG_ORDER, CONSULTATION, TEST, etc.
    related_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True)))
    status: str = Field(default="PENDING", max_length=20, index=True)  # PENDING, COMPLETED, FAILED, CANCELLED
    reference_number: Optional[str] = Field(default=None, max_length=100, unique=True, index=True)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="transactions")
    payment_method: Optional[PaymentMethod] = Relationship(back_populates="transactions")


class AuditLog(SQLModel, table=True):
    """Audit logs for tracking user actions"""
    
    __tablename__ = "audit_logs"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)
    action: str = Field(max_length=100, index=True)
    table_name: Optional[str] = Field(default=None, max_length=100, index=True)
    record_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True)))
    old_values: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    new_values: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="audit_logs")


class MedicalRecordAccess(SQLModel, table=True):
    """Access logs for medical records"""
    
    __tablename__ = "medical_record_access"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    accessor_id: UUID = Field(foreign_key="users.id", index=True)
    accessor_type: str = Field(max_length=20, index=True)  # DOCTOR, PATIENT, ADMIN, AI_SYSTEM
    access_type: str = Field(max_length=20, index=True)  # VIEW, CREATE, UPDATE, DELETE
    record_type: str = Field(max_length=50)  # VITALS, CONDITIONS, PRESCRIPTIONS, etc.
    record_id: Optional[UUID] = Field(default=None, sa_column=Column(PGUUID(as_uuid=True)))
    purpose: Optional[str] = Field(default=None, max_length=100)  # TREATMENT, CONSULTATION, BILLING, etc.
    consent_given: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="medical_record_accesses")
    accessor: User = Relationship(back_populates="medical_record_accesses")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .patients import Patient
    from .doctors import Doctor
    from .hospitals import Hospital, HospitalStaff
    from .pharmacy import Pharmacy, BarcodeScan
    from .insurance import InsuranceCompany

