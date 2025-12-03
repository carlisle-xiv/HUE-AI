from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class ForecastGranularity(str, Enum):
    """Granularity levels for demand forecasting."""
    PER_PHARMACY = "per_pharmacy"
    PER_DRUG = "per_drug"
    PER_DRUG_PHARMACY = "per_drug_pharmacy"
    AGGREGATE = "aggregate"


class ForecastHorizon(int, Enum):
    """Forecast horizon in days."""
    SEVEN_DAYS = 7
    THIRTY_DAYS = 30
    NINETY_DAYS = 90


class AnomalyType(str, Enum):
    """Types of demand anomalies."""
    SPIKE = "spike"
    DROP = "drop"
    TREND_CHANGE = "trend_change"


class ExpiryRiskLevel(str, Enum):
    """Risk levels for expiry prediction."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SeasonalPattern(str, Enum):
    """Types of seasonal patterns."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    DISEASE_SEASON = "disease_season"


# ============================================================================
# Request Schemas
# ============================================================================

class DemandForecastRequest(BaseModel):
    """Request schema for generating demand forecasts."""
    
    granularity: ForecastGranularity = Field(
        default=ForecastGranularity.PER_DRUG_PHARMACY,
        description="Level of granularity for the forecast"
    )
    horizon_days: ForecastHorizon = Field(
        default=ForecastHorizon.THIRTY_DAYS,
        description="Number of days to forecast ahead"
    )
    pharmacy_id: Optional[UUID] = Field(
        default=None,
        description="Specific pharmacy ID (required for per_pharmacy and per_drug_pharmacy)"
    )
    drug_id: Optional[UUID] = Field(
        default=None,
        description="Specific drug/pharmacy_code ID (required for per_drug and per_drug_pharmacy)"
    )
    include_confidence_intervals: bool = Field(
        default=True,
        description="Include upper and lower bounds in forecast"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "granularity": "per_drug_pharmacy",
                "horizon_days": 30,
                "pharmacy_id": "123e4567-e89b-12d3-a456-426614174000",
                "drug_id": "123e4567-e89b-12d3-a456-426614174001",
                "include_confidence_intervals": True
            }
        }


class ExpiryRiskRequest(BaseModel):
    """Request schema for expiry risk analysis."""
    
    pharmacy_id: Optional[UUID] = Field(
        default=None,
        description="Filter by specific pharmacy"
    )
    drug_id: Optional[UUID] = Field(
        default=None,
        description="Filter by specific drug"
    )
    days_ahead: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Days ahead to analyze for expiry risk"
    )
    min_risk_level: ExpiryRiskLevel = Field(
        default=ExpiryRiskLevel.MEDIUM,
        description="Minimum risk level to include in results"
    )


class ReorderRecommendationRequest(BaseModel):
    """Request schema for reorder recommendations."""
    
    pharmacy_id: UUID = Field(
        description="Pharmacy ID to generate recommendations for"
    )
    forecast_horizon: ForecastHorizon = Field(
        default=ForecastHorizon.THIRTY_DAYS,
        description="Forecast horizon for demand estimation"
    )
    safety_stock_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Days of safety stock to maintain"
    )
    lead_time_days: int = Field(
        default=3,
        ge=1,
        le=14,
        description="Expected lead time for orders"
    )


# ============================================================================
# Response Schemas
# ============================================================================

class ForecastDataPoint(BaseModel):
    """Single data point in a forecast."""
    
    forecast_date: date = Field(description="Forecast date")
    predicted_quantity: float = Field(description="Predicted demand quantity")
    lower_bound: Optional[float] = Field(
        default=None,
        description="Lower bound of confidence interval"
    )
    upper_bound: Optional[float] = Field(
        default=None,
        description="Upper bound of confidence interval"
    )


class DrugForecast(BaseModel):
    """Forecast for a specific drug."""
    
    drug_id: UUID = Field(description="Drug/pharmacy_code ID")
    drug_name: str = Field(description="Drug name")
    generic_name: Optional[str] = Field(default=None, description="Generic drug name")
    therapeutic_class: Optional[str] = Field(default=None, description="Drug therapeutic class")
    forecast_points: list[ForecastDataPoint] = Field(description="Forecast data points")
    total_predicted_demand: float = Field(description="Total predicted demand over horizon")
    average_daily_demand: float = Field(description="Average daily predicted demand")
    trend_direction: str = Field(description="Trend direction: increasing, decreasing, stable")
    confidence_score: float = Field(ge=0, le=1, description="Model confidence score")


class PharmacyForecast(BaseModel):
    """Forecast for a specific pharmacy."""
    
    pharmacy_id: UUID = Field(description="Pharmacy ID")
    pharmacy_name: str = Field(description="Pharmacy name")
    drug_forecasts: list[DrugForecast] = Field(description="Forecasts per drug")
    total_predicted_orders: float = Field(description="Total predicted orders")


class DemandForecastResponse(BaseModel):
    """Response schema for demand forecast."""
    
    request_id: UUID = Field(description="Unique request identifier")
    granularity: ForecastGranularity = Field(description="Forecast granularity")
    horizon_days: int = Field(description="Forecast horizon in days")
    generated_at: datetime = Field(description="Timestamp of forecast generation")
    forecast_start_date: date = Field(description="Start date of forecast")
    forecast_end_date: date = Field(description="End date of forecast")
    
    # Results based on granularity
    pharmacy_forecasts: Optional[list[PharmacyForecast]] = Field(
        default=None,
        description="Forecasts grouped by pharmacy"
    )
    drug_forecasts: Optional[list[DrugForecast]] = Field(
        default=None,
        description="Forecasts grouped by drug (aggregate)"
    )
    
    # Metadata
    model_version: str = Field(default="prophet-1.0", description="Model version used")
    data_points_used: int = Field(description="Number of historical data points used")
    processing_time_seconds: float = Field(description="Time taken to generate forecast")


class ExpiryRiskItem(BaseModel):
    """Single item at risk of expiry."""
    
    pharmacy_id: UUID = Field(description="Pharmacy ID")
    pharmacy_name: str = Field(description="Pharmacy name")
    drug_id: UUID = Field(description="Drug ID")
    drug_name: str = Field(description="Drug name")
    current_quantity: int = Field(description="Current inventory quantity")
    expiry_date: date = Field(description="Expiry date")
    days_until_expiry: int = Field(description="Days until expiry")
    predicted_demand_until_expiry: float = Field(
        description="Predicted demand before expiry"
    )
    estimated_waste_quantity: float = Field(
        description="Estimated quantity that will expire"
    )
    risk_level: ExpiryRiskLevel = Field(description="Risk level")
    recommended_action: str = Field(description="Recommended action to take")
    potential_loss_value: Decimal = Field(description="Potential financial loss")


class ExpiryRiskResponse(BaseModel):
    """Response schema for expiry risk analysis."""
    
    analysis_date: datetime = Field(description="Analysis timestamp")
    total_items_at_risk: int = Field(description="Total items at risk")
    total_potential_loss: Decimal = Field(description="Total potential financial loss")
    risk_items: list[ExpiryRiskItem] = Field(description="Items at risk of expiry")
    summary_by_risk_level: dict[str, int] = Field(
        description="Count of items by risk level"
    )


class SeasonalityPattern(BaseModel):
    """Detected seasonal pattern."""
    
    pattern_type: SeasonalPattern = Field(description="Type of pattern")
    strength: float = Field(ge=0, le=1, description="Pattern strength (0-1)")
    peak_periods: list[str] = Field(description="Peak demand periods")
    low_periods: list[str] = Field(description="Low demand periods")
    description: str = Field(description="Human-readable description")


class SeasonalityResponse(BaseModel):
    """Response schema for seasonality analysis."""
    
    drug_id: UUID = Field(description="Drug ID analyzed")
    drug_name: str = Field(description="Drug name")
    analysis_period_days: int = Field(description="Days of data analyzed")
    patterns_detected: list[SeasonalityPattern] = Field(
        description="Detected patterns"
    )
    has_strong_seasonality: bool = Field(description="Whether strong seasonality exists")
    recommendations: list[str] = Field(description="Stock recommendations based on patterns")


class DemandAnomaly(BaseModel):
    """Detected demand anomaly."""
    
    anomaly_id: UUID = Field(description="Anomaly identifier")
    detected_at: datetime = Field(description="When anomaly was detected")
    anomaly_type: AnomalyType = Field(description="Type of anomaly")
    pharmacy_id: Optional[UUID] = Field(default=None, description="Affected pharmacy")
    drug_id: Optional[UUID] = Field(default=None, description="Affected drug")
    drug_name: Optional[str] = Field(default=None, description="Drug name")
    
    anomaly_date: date = Field(description="Date of anomalous demand")
    expected_demand: float = Field(description="Expected demand")
    actual_demand: float = Field(description="Actual observed demand")
    deviation_percentage: float = Field(description="Percentage deviation from expected")
    severity: str = Field(description="Severity: low, medium, high")
    
    possible_causes: list[str] = Field(description="Possible causes")
    recommended_actions: list[str] = Field(description="Recommended actions")


class AnomalyDetectionResponse(BaseModel):
    """Response schema for anomaly detection."""
    
    analysis_period_start: date = Field(description="Start of analysis period")
    analysis_period_end: date = Field(description="End of analysis period")
    total_anomalies_detected: int = Field(description="Total anomalies found")
    anomalies: list[DemandAnomaly] = Field(description="Detected anomalies")
    summary_by_type: dict[str, int] = Field(description="Count by anomaly type")


class ReorderItem(BaseModel):
    """Single item to reorder."""
    
    drug_id: UUID = Field(description="Drug ID")
    drug_name: str = Field(description="Drug name")
    current_stock: int = Field(description="Current inventory")
    predicted_demand: float = Field(description="Predicted demand for horizon")
    safety_stock: int = Field(description="Recommended safety stock")
    reorder_quantity: int = Field(description="Recommended reorder quantity")
    urgency: str = Field(description="Urgency: immediate, soon, planned")
    days_until_stockout: Optional[int] = Field(
        default=None,
        description="Estimated days until stockout"
    )
    estimated_cost: Optional[Decimal] = Field(
        default=None,
        description="Estimated reorder cost"
    )


class ReorderRecommendationResponse(BaseModel):
    """Response schema for reorder recommendations."""
    
    pharmacy_id: UUID = Field(description="Pharmacy ID")
    pharmacy_name: str = Field(description="Pharmacy name")
    generated_at: datetime = Field(description="Generation timestamp")
    forecast_horizon_days: int = Field(description="Forecast horizon used")
    
    immediate_reorders: list[ReorderItem] = Field(
        description="Items needing immediate reorder"
    )
    upcoming_reorders: list[ReorderItem] = Field(
        description="Items to reorder soon"
    )
    total_reorder_value: Decimal = Field(description="Total estimated reorder cost")
    summary: str = Field(description="Summary of recommendations")

