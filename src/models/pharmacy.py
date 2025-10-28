"""
Pharmacy-related models including pharmacies, inventory, orders, and drug tracking.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Integer, Boolean, DECIMAL, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from .enums import DrugOrderStatus


class Pharmacy(SQLModel, table=True):
    """Pharmacy profile"""
    
    __tablename__ = "pharmacies"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    name: str = Field(max_length=255, index=True)
    license_number: str = Field(max_length=100, unique=True, index=True)
    address: dict = Field(sa_column=Column(JSONB))
    phone_number: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    operating_hours: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    delivery_available: bool = Field(default=False, index=True)
    delivery_radius_km: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 2)))
    is_active: bool = Field(default=True)
    rating_average: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(3, 2)))
    total_ratings: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="pharmacy")
    inventory: list["PharmacyInventory"] = Relationship(back_populates="pharmacy")
    drug_orders: list["DrugOrder"] = Relationship(back_populates="pharmacy")


class PharmacyInventory(SQLModel, table=True):
    """Pharmacy inventory management"""
    
    __tablename__ = "pharmacy_inventory"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    pharmacy_id: UUID = Field(foreign_key="pharmacies.id", index=True)
    pharmacy_code_id: UUID = Field(foreign_key="pharmacy_codes.id", index=True)
    quantity_available: int = Field(default=0)
    unit_price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    expiry_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    batch_number: Optional[str] = Field(default=None, max_length=100)
    is_insurance_covered: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    pharmacy: Pharmacy = Relationship(back_populates="inventory")
    pharmacy_code: "PharmacyCode" = Relationship(back_populates="pharmacy_inventory")
    drug_order_items: list["DrugOrderItem"] = Relationship(back_populates="pharmacy_inventory")


class DrugOrder(SQLModel, table=True):
    """Drug order from patient to pharmacy"""
    
    __tablename__ = "drug_orders"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    patient_id: UUID = Field(foreign_key="patients.id", index=True)
    pharmacy_id: UUID = Field(foreign_key="pharmacies.id", index=True)
    prescription_id: Optional[UUID] = Field(default=None, foreign_key="prescriptions.id", index=True)
    order_number: str = Field(max_length=50, unique=True, index=True)
    order_type: str = Field(max_length=20)  # PRESCRIPTION, OVER_COUNTER, SPECIAL_REQUEST
    total_amount: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    insurance_covered_amount: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(10, 2)))
    patient_pay_amount: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    status: str = Field(default="PENDING", max_length=20, index=True)  # PENDING, APPROVED, REJECTED, PREPARED, SHIPPED, DELIVERED, COMPLETED
    delivery_method: Optional[str] = Field(default=None, max_length=20)  # PICKUP, DELIVERY
    delivery_address: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    pharmacy_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    patient_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: "Patient" = Relationship(back_populates="drug_orders")
    pharmacy: Pharmacy = Relationship(back_populates="drug_orders")
    prescription: Optional["Prescription"] = Relationship(back_populates="drug_orders")
    items: list["DrugOrderItem"] = Relationship(back_populates="drug_order")


class DrugOrderItem(SQLModel, table=True):
    """Individual items in a drug order"""
    
    __tablename__ = "drug_order_items"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    drug_order_id: UUID = Field(foreign_key="drug_orders.id", index=True)
    pharmacy_inventory_id: UUID = Field(foreign_key="pharmacy_inventory.id", index=True)
    quantity_ordered: int = Field()
    unit_price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    total_price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    drug_order: DrugOrder = Relationship(back_populates="items")
    pharmacy_inventory: PharmacyInventory = Relationship(back_populates="drug_order_items")


class DrugBarcode(SQLModel, table=True):
    """Drug barcode information for verification"""
    
    __tablename__ = "drug_barcodes"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    barcode: str = Field(max_length=50, unique=True, index=True)
    pharmacy_code_id: UUID = Field(foreign_key="pharmacy_codes.id", index=True)
    manufacturer: Optional[str] = Field(default=None, max_length=255, index=True)
    batch_number: Optional[str] = Field(default=None, max_length=100)
    manufacturing_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    expiry_date: Optional[date] = Field(default=None, sa_column=Column(Date, index=True))
    is_authentic: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    pharmacy_code: "PharmacyCode" = Relationship(back_populates="drug_barcodes")
    barcode_scans: list["BarcodeScan"] = Relationship(back_populates="drug_barcode")


class BarcodeScan(SQLModel, table=True):
    """Barcode scan records"""
    
    __tablename__ = "barcode_scans"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    user_id: UUID = Field(foreign_key="users.id", index=True)
    barcode: str = Field(max_length=50, index=True)
    scan_result: str = Field(max_length=20, index=True)  # VALID, INVALID, EXPIRED, RECALLED
    drug_barcode_id: Optional[UUID] = Field(default=None, foreign_key="drug_barcodes.id")
    location_data: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    user: "User" = Relationship(back_populates="barcode_scans")
    drug_barcode: Optional[DrugBarcode] = Relationship(back_populates="barcode_scans")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import User
    from .patients import Patient
    from .reference import PharmacyCode
    from .prescriptions import Prescription

