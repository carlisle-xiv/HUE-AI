from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, Date, Integer, Boolean, DECIMAL, func, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB


class DemandForecast(SQLModel, table=True):
    """
    Stored demand forecast predictions.
    Allows caching forecasts and tracking model performance over time.
    """
    
    __tablename__ = "demand_forecasts"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    
    # Scope identifiers
    pharmacy_id: Optional[UUID] = Field(
        default=None, 
        foreign_key="pharmacies.id", 
        index=True,
        description="Pharmacy ID (null for aggregate forecasts)"
    )
    drug_id: Optional[UUID] = Field(
        default=None, 
        foreign_key="pharmacy_codes.id", 
        index=True,
        description="Drug/pharmacy_code ID"
    )
    
    # Forecast parameters
    granularity: str = Field(
        max_length=30, 
        index=True,
        description="Forecast granularity: per_pharmacy, per_drug, per_drug_pharmacy, aggregate"
    )
    horizon_days: int = Field(
        description="Forecast horizon in days"
    )
    forecast_start_date: date = Field(
        sa_column=Column(Date, index=True),
        description="Start date of forecast period"
    )
    forecast_end_date: date = Field(
        sa_column=Column(Date),
        description="End date of forecast period"
    )
    
    # Forecast data - stored as JSON array of {date, predicted, lower, upper}
    forecast_data: dict = Field(
        sa_column=Column(JSONB),
        description="Array of forecast data points"
    )
    
    # Aggregate metrics
    total_predicted_demand: Decimal = Field(
        sa_column=Column(DECIMAL(12, 2)),
        description="Total predicted demand over horizon"
    )
    average_daily_demand: Decimal = Field(
        sa_column=Column(DECIMAL(10, 2)),
        description="Average daily predicted demand"
    )
    trend_direction: str = Field(
        max_length=20,
        description="Trend direction: increasing, decreasing, stable"
    )
    confidence_score: Decimal = Field(
        sa_column=Column(DECIMAL(4, 3)),
        description="Model confidence score (0-1)"
    )
    
    # Model metadata
    model_version: str = Field(
        default="prophet-1.0", 
        max_length=50,
        description="Version of the forecasting model"
    )
    training_data_points: int = Field(
        description="Number of historical data points used for training"
    )
    training_period_start: Optional[date] = Field(
        default=None,
        sa_column=Column(Date),
        description="Start of training data period"
    )
    training_period_end: Optional[date] = Field(
        default=None,
        sa_column=Column(Date),
        description="End of training data period"
    )
    
    # Performance tracking (filled in after forecast period ends)
    actual_demand: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(DECIMAL(12, 2)),
        description="Actual demand (for accuracy tracking)"
    )
    forecast_error_mape: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(DECIMAL(6, 2)),
        description="Mean Absolute Percentage Error"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # Relationships
    pharmacy: Optional["Pharmacy"] = Relationship(back_populates="demand_forecasts")
    drug: Optional["PharmacyCode"] = Relationship(back_populates="demand_forecasts")
    
    __table_args__ = (
        Index('ix_demand_forecasts_scope', 'pharmacy_id', 'drug_id', 'granularity'),
        Index('ix_demand_forecasts_date_range', 'forecast_start_date', 'forecast_end_date'),
    )


class DemandAnomaly(SQLModel, table=True):
    """
    Detected demand anomalies for alerting and analysis.
    """
    
    __tablename__ = "demand_anomalies"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    
    # Scope identifiers
    pharmacy_id: Optional[UUID] = Field(
        default=None, 
        foreign_key="pharmacies.id", 
        index=True
    )
    drug_id: Optional[UUID] = Field(
        default=None, 
        foreign_key="pharmacy_codes.id", 
        index=True
    )
    
    # Anomaly details
    anomaly_type: str = Field(
        max_length=30, 
        index=True,
        description="Type: spike, drop, trend_change"
    )
    anomaly_date: date = Field(
        sa_column=Column(Date, index=True),
        description="Date when anomaly occurred"
    )
    
    # Deviation metrics
    expected_demand: Decimal = Field(
        sa_column=Column(DECIMAL(10, 2)),
        description="Expected demand based on forecast"
    )
    actual_demand: Decimal = Field(
        sa_column=Column(DECIMAL(10, 2)),
        description="Actual observed demand"
    )
    deviation_percentage: Decimal = Field(
        sa_column=Column(DECIMAL(8, 2)),
        description="Percentage deviation from expected"
    )
    deviation_sigma: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(DECIMAL(6, 2)),
        description="Number of standard deviations from mean"
    )
    
    # Classification
    severity: str = Field(
        max_length=20, 
        index=True,
        description="Severity: low, medium, high, critical"
    )
    
    # Analysis
    possible_causes: Optional[list] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="List of possible causes"
    )
    recommended_actions: Optional[list] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="List of recommended actions"
    )
    
    # Status tracking
    is_acknowledged: bool = Field(
        default=False,
        index=True,
        description="Whether anomaly has been acknowledged"
    )
    acknowledged_by: Optional[UUID] = Field(
        default=None,
        sa_column=Column(PGUUID(as_uuid=True)),
        description="User who acknowledged"
    )
    acknowledged_at: Optional[datetime] = Field(
        default=None
    )
    resolution_notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text)
    )
    
    # Timestamps
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # Relationships
    pharmacy: Optional["Pharmacy"] = Relationship(back_populates="demand_anomalies")
    drug: Optional["PharmacyCode"] = Relationship(back_populates="demand_anomalies")
    
    __table_args__ = (
        Index('ix_demand_anomalies_scope', 'pharmacy_id', 'drug_id'),
        Index('ix_demand_anomalies_unack', 'is_acknowledged', 'detected_at'),
    )


class SeasonalityPattern(SQLModel, table=True):
    """
    Stored seasonal patterns for drugs.
    """
    
    __tablename__ = "seasonality_patterns"
    
    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    )
    
    drug_id: UUID = Field(
        foreign_key="pharmacy_codes.id", 
        index=True
    )
    
    # Pattern details
    pattern_type: str = Field(
        max_length=30, 
        index=True,
        description="Type: weekly, monthly, yearly, disease_season"
    )
    strength: Decimal = Field(
        sa_column=Column(DECIMAL(4, 3)),
        description="Pattern strength (0-1)"
    )
    
    # Pattern data
    pattern_data: dict = Field(
        sa_column=Column(JSONB),
        description="Detailed pattern data (peak periods, low periods, etc.)"
    )
    
    # Analysis metadata
    analysis_period_days: int = Field(
        description="Days of data used in analysis"
    )
    analysis_start_date: date = Field(
        sa_column=Column(Date)
    )
    analysis_end_date: date = Field(
        sa_column=Column(Date)
    )
    
    # Description
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Human-readable pattern description"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # Relationships
    drug: "PharmacyCode" = Relationship(back_populates="seasonality_patterns")


# Forward references for relationships
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models.pharmacy import Pharmacy
    from src.models.reference import PharmacyCode

