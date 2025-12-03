import logging
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from src.database import get_db

from .schemas import (
    AnomalyDetectionResponse,
    DemandForecastRequest,
    DemandForecastResponse,
    ExpiryRiskRequest,
    ExpiryRiskResponse,
    ExpiryRiskLevel,
    ForecastGranularity,
    ForecastHorizon,
    ReorderRecommendationRequest,
    ReorderRecommendationResponse,
    SeasonalityResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/clinical-prediction",
    tags=["Clinical Data Prediction"],
)


# ============================================================================
# Demand Forecasting Endpoints
# ============================================================================

@router.post(
    "/forecast/demand",
    response_model=DemandForecastResponse,
    summary="Generate demand forecast",
    description="""
    Generate medicine demand forecasts with configurable granularity and horizon.
    
    **Granularities:**
    - `per_pharmacy`: Forecast total demand for a specific pharmacy
    - `per_drug`: Forecast demand for a specific drug across all pharmacies
    - `per_drug_pharmacy`: Forecast demand for a specific drug at a specific pharmacy
    - `aggregate`: Forecast platform-wide demand per drug
    
    **Horizons:** 7, 30, or 90 days
    """
)
async def generate_demand_forecast(
    request: DemandForecastRequest,
    session: Session = Depends(get_db)
) -> DemandForecastResponse:
    """Generate demand forecast based on historical data."""
    from .demand_forecasting.service import DemandForecastingService
    
    logger.info(
        f"Generating demand forecast: granularity={request.granularity}, "
        f"horizon={request.horizon_days} days"
    )
    
    try:
        service = DemandForecastingService(session)
        response = await service.generate_forecast(request)
        return response
    except ValueError as e:
        logger.warning(f"Invalid forecast request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate forecast")


@router.get(
    "/forecast/pharmacy/{pharmacy_id}",
    response_model=DemandForecastResponse,
    summary="Get forecasts for a pharmacy",
    description="Retrieve demand forecasts for all drugs at a specific pharmacy."
)
async def get_pharmacy_forecast(
    pharmacy_id: UUID,
    horizon_days: ForecastHorizon = Query(
        default=ForecastHorizon.THIRTY_DAYS,
        description="Forecast horizon in days"
    ),
    session: Session = Depends(get_db)
) -> DemandForecastResponse:
    """Get demand forecasts for a specific pharmacy."""
    from .demand_forecasting.service import DemandForecastingService
    
    logger.info(f"Getting forecast for pharmacy {pharmacy_id}")
    
    try:
        service = DemandForecastingService(session)
        request = DemandForecastRequest(
            granularity=ForecastGranularity.PER_PHARMACY,
            horizon_days=horizon_days,
            pharmacy_id=pharmacy_id
        )
        response = await service.generate_forecast(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting pharmacy forecast: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get pharmacy forecast")


@router.get(
    "/forecast/drug/{drug_id}",
    response_model=DemandForecastResponse,
    summary="Get forecasts for a drug",
    description="Retrieve platform-wide demand forecasts for a specific drug."
)
async def get_drug_forecast(
    drug_id: UUID,
    horizon_days: ForecastHorizon = Query(
        default=ForecastHorizon.THIRTY_DAYS,
        description="Forecast horizon in days"
    ),
    session: Session = Depends(get_db)
) -> DemandForecastResponse:
    """Get demand forecasts for a specific drug."""
    from .demand_forecasting.service import DemandForecastingService
    
    logger.info(f"Getting forecast for drug {drug_id}")
    
    try:
        service = DemandForecastingService(session)
        request = DemandForecastRequest(
            granularity=ForecastGranularity.PER_DRUG,
            horizon_days=horizon_days,
            drug_id=drug_id
        )
        response = await service.generate_forecast(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting drug forecast: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get drug forecast")


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.post(
    "/analytics/expiry-risk",
    response_model=ExpiryRiskResponse,
    summary="Get expiry risk report",
    description="""
    Analyze inventory for drugs at risk of expiring before being sold.
    Compares forecasted demand with current inventory and expiry dates.
    """
)
async def get_expiry_risk(
    request: ExpiryRiskRequest,
    session: Session = Depends(get_db)
) -> ExpiryRiskResponse:
    """Get expiry risk analysis."""
    from .analytics.expiry_predictor import ExpiryPredictor
    
    logger.info(f"Analyzing expiry risk for {request.days_ahead} days ahead")
    
    try:
        predictor = ExpiryPredictor(session)
        response = await predictor.analyze_expiry_risk(request)
        return response
    except Exception as e:
        logger.error(f"Error analyzing expiry risk: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze expiry risk")


@router.get(
    "/analytics/seasonality/{drug_id}",
    response_model=SeasonalityResponse,
    summary="Get seasonal patterns",
    description="""
    Analyze demand patterns for a specific drug to identify:
    - Weekly cycles (weekday vs weekend)
    - Monthly patterns
    - Disease season spikes (malaria season, flu season)
    """
)
async def get_seasonality(
    drug_id: UUID,
    analysis_days: int = Query(
        default=365,
        ge=90,
        le=730,
        description="Days of historical data to analyze"
    ),
    session: Session = Depends(get_db)
) -> SeasonalityResponse:
    """Get seasonal pattern analysis for a drug."""
    from .analytics.seasonality_analyzer import SeasonalityAnalyzer
    
    logger.info(f"Analyzing seasonality for drug {drug_id}")
    
    try:
        analyzer = SeasonalityAnalyzer(session)
        response = await analyzer.analyze_seasonality(drug_id, analysis_days)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing seasonality: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze seasonality")


@router.get(
    "/analytics/anomalies",
    response_model=AnomalyDetectionResponse,
    summary="Get detected anomalies",
    description="""
    Detect unusual demand patterns including:
    - Sudden spikes (potential outbreak signals)
    - Unexpected drops (supply chain or data issues)
    - Trend changes
    """
)
async def get_anomalies(
    pharmacy_id: Optional[UUID] = Query(
        default=None,
        description="Filter by pharmacy"
    ),
    drug_id: Optional[UUID] = Query(
        default=None,
        description="Filter by drug"
    ),
    days_back: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Days of history to analyze"
    ),
    session: Session = Depends(get_db)
) -> AnomalyDetectionResponse:
    """Get detected demand anomalies."""
    from .analytics.anomaly_detector import AnomalyDetector
    
    logger.info(f"Detecting anomalies for past {days_back} days")
    
    try:
        detector = AnomalyDetector(session)
        response = await detector.detect_anomalies(
            pharmacy_id=pharmacy_id,
            drug_id=drug_id,
            days_back=days_back
        )
        return response
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to detect anomalies")


# ============================================================================
# Reorder Recommendations Endpoint
# ============================================================================

@router.post(
    "/forecast/reorder-recommendations",
    response_model=ReorderRecommendationResponse,
    summary="Get smart reorder suggestions",
    description="""
    Generate intelligent reorder recommendations based on:
    - Demand forecasts
    - Current inventory levels
    - Safety stock requirements
    - Lead time considerations
    """
)
async def get_reorder_recommendations(
    request: ReorderRecommendationRequest,
    session: Session = Depends(get_db)
) -> ReorderRecommendationResponse:
    """Get reorder recommendations for a pharmacy."""
    from .demand_forecasting.service import DemandForecastingService
    
    logger.info(f"Generating reorder recommendations for pharmacy {request.pharmacy_id}")
    
    try:
        service = DemandForecastingService(session)
        response = await service.generate_reorder_recommendations(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating reorder recommendations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate reorder recommendations"
        )


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@router.get(
    "/health",
    summary="Health check",
    description="Check the health status of the Clinical Data Prediction module."
)
async def health_check():
    """Health check for the clinical prediction module."""
    return {
        "status": "healthy",
        "module": "clinical_data_prediction",
        "version": "1.0.0",
        "features": [
            "demand_forecasting",
            "expiry_prediction",
            "seasonality_analysis",
            "anomaly_detection"
        ]
    }

