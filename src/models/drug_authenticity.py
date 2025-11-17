"""
Drug authenticity verification models for caching search results.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text, DECIMAL, ARRAY, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB


class DrugAuthenticityCheck(SQLModel, table=True):
    """Drug authenticity check results with caching"""
    
    __tablename__ = "drug_authenticity_checks"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    drug_name: str = Field(max_length=255, index=True)
    drug_name_normalized: str = Field(max_length=255, index=True)  # Lowercase for cache lookup
    search_query: str = Field(max_length=500)
    authenticity_status: str = Field(max_length=20, index=True)  # AUTHENTIC, COUNTERFEIT, UNKNOWN
    confidence_score: Decimal = Field(sa_column=Column(DECIMAL(3, 2)))  # 0.00 to 1.00
    detailed_report: dict = Field(sa_column=Column(JSONB))  # manufacturer_info, regulatory_status, warnings
    sources: list[str] = Field(default=[], sa_column=Column(ARRAY(String)))  # URLs of verification sources
    search_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    expires_at: datetime = Field(index=True)  # Cache expiration (30 days from search)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def is_expired(self) -> bool:
        """Check if the cached result has expired"""
        return datetime.utcnow() > self.expires_at
    
    @staticmethod
    def calculate_expiry_date(days: int = 30) -> datetime:
        """Calculate expiry date from now"""
        return datetime.utcnow() + timedelta(days=days)

