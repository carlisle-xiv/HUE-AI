import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

from src.models.pharmacy import Pharmacy, PharmacyInventory
from src.models.reference import PharmacyCode

from ..schemas import (
    DemandForecastRequest,
    DemandForecastResponse,
    DrugForecast,
    ForecastDataPoint,
    ForecastGranularity,
    ForecastHorizon,
    PharmacyForecast,
    ReorderItem,
    ReorderRecommendationRequest,
    ReorderRecommendationResponse,
)
from .data_pipeline import DemandDataPipeline
from .prophet_forecaster import ProphetForecaster
from .models import DemandForecast as DemandForecastModel

# Configure logging
logger = logging.getLogger(__name__)


class DemandForecastingService:
    """
    Main service for demand forecasting.
    Supports all 4 granularity levels and 3 forecast horizons.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.pipeline = DemandDataPipeline(session)
    
    async def generate_forecast(
        self,
        request: DemandForecastRequest
    ) -> DemandForecastResponse:
        """
        Generate demand forecast based on request parameters.
        
        Args:
            request: DemandForecastRequest with granularity, horizon, and IDs
            
        Returns:
            DemandForecastResponse with forecasts
        """
        start_time = datetime.utcnow()
        request_id = uuid4()
        
        logger.info(
            f"Processing forecast request {request_id}: "
            f"granularity={request.granularity}, horizon={request.horizon_days}"
        )
        
        # Validate request based on granularity
        self._validate_request(request)
        
        # Generate forecast based on granularity
        if request.granularity == ForecastGranularity.PER_DRUG_PHARMACY:
            response = await self._forecast_per_drug_pharmacy(request, request_id)
        elif request.granularity == ForecastGranularity.PER_PHARMACY:
            response = await self._forecast_per_pharmacy(request, request_id)
        elif request.granularity == ForecastGranularity.PER_DRUG:
            response = await self._forecast_per_drug(request, request_id)
        else:  # AGGREGATE
            response = await self._forecast_aggregate(request, request_id)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        response.processing_time_seconds = processing_time
        
        logger.info(f"Completed forecast request {request_id} in {processing_time:.2f}s")
        
        return response
    
    def _validate_request(self, request: DemandForecastRequest) -> None:
        """Validate request parameters based on granularity."""
        if request.granularity == ForecastGranularity.PER_DRUG_PHARMACY:
            if not request.pharmacy_id or not request.drug_id:
                raise ValueError(
                    "Both pharmacy_id and drug_id are required for per_drug_pharmacy granularity"
                )
        elif request.granularity == ForecastGranularity.PER_PHARMACY:
            if not request.pharmacy_id:
                raise ValueError(
                    "pharmacy_id is required for per_pharmacy granularity"
                )
        elif request.granularity == ForecastGranularity.PER_DRUG:
            if not request.drug_id:
                raise ValueError(
                    "drug_id is required for per_drug granularity"
                )
    
    async def _forecast_per_drug_pharmacy(
        self,
        request: DemandForecastRequest,
        request_id: UUID
    ) -> DemandForecastResponse:
        """Generate forecast for specific drug at specific pharmacy."""
        # Get data
        df = self.pipeline.get_demand_data_per_drug_pharmacy(
            request.pharmacy_id,
            request.drug_id
        )
        
        # Get metadata
        drug_info = self.pipeline.get_drug_info(request.drug_id)
        pharmacy_info = self.pipeline.get_pharmacy_info(request.pharmacy_id)
        
        if not drug_info:
            raise ValueError(f"Drug not found: {request.drug_id}")
        if not pharmacy_info:
            raise ValueError(f"Pharmacy not found: {request.pharmacy_id}")
        
        # Generate forecast
        forecaster = ProphetForecaster()
        forecaster.fit(df)
        forecast = forecaster.predict(request.horizon_days)
        
        # Build drug forecast
        total_demand, avg_demand = ProphetForecaster.calculate_total_demand(forecast)
        
        drug_forecast = DrugForecast(
            drug_id=request.drug_id,
            drug_name=drug_info['drug_name'],
            generic_name=drug_info.get('generic_name'),
            therapeutic_class=drug_info.get('therapeutic_class'),
            forecast_points=self._convert_forecast_points(
                forecast, request.include_confidence_intervals
            ),
            total_predicted_demand=total_demand,
            average_daily_demand=avg_demand,
            trend_direction=forecaster.get_trend_direction(),
            confidence_score=forecaster.get_confidence_score()
        )
        
        # Build pharmacy forecast
        pharmacy_forecast = PharmacyForecast(
            pharmacy_id=request.pharmacy_id,
            pharmacy_name=pharmacy_info['pharmacy_name'],
            drug_forecasts=[drug_forecast],
            total_predicted_orders=total_demand
        )
        
        # Save forecast to database
        await self._save_forecast(
            request, drug_forecast, pharmacy_info, forecaster, len(df)
        )
        
        return DemandForecastResponse(
            request_id=request_id,
            granularity=request.granularity,
            horizon_days=request.horizon_days,
            generated_at=datetime.utcnow(),
            forecast_start_date=datetime.utcnow().date() + timedelta(days=1),
            forecast_end_date=datetime.utcnow().date() + timedelta(days=request.horizon_days),
            pharmacy_forecasts=[pharmacy_forecast],
            drug_forecasts=None,
            model_version=ProphetForecaster.MODEL_VERSION,
            data_points_used=len(df),
            processing_time_seconds=0  # Will be filled in
        )
    
    async def _forecast_per_pharmacy(
        self,
        request: DemandForecastRequest,
        request_id: UUID
    ) -> DemandForecastResponse:
        """Generate forecast for all drugs at a specific pharmacy."""
        # Get pharmacy info
        pharmacy_info = self.pipeline.get_pharmacy_info(request.pharmacy_id)
        if not pharmacy_info:
            raise ValueError(f"Pharmacy not found: {request.pharmacy_id}")
        
        # Get data for all drugs
        drug_data = self.pipeline.get_demand_data_per_pharmacy(request.pharmacy_id)
        
        if not drug_data:
            logger.warning(f"No demand data found for pharmacy {request.pharmacy_id}")
            return self._create_empty_response(
                request_id, request, pharmacy_info=pharmacy_info
            )
        
        drug_forecasts = []
        total_data_points = 0
        
        for drug_id, df in drug_data.items():
            total_data_points += len(df)
            
            drug_info = self.pipeline.get_drug_info(drug_id)
            if not drug_info:
                continue
            
            # Generate forecast for each drug
            forecaster = ProphetForecaster()
            forecaster.fit(df)
            forecast = forecaster.predict(request.horizon_days)
            
            total_demand, avg_demand = ProphetForecaster.calculate_total_demand(forecast)
            
            drug_forecast = DrugForecast(
                drug_id=drug_id,
                drug_name=drug_info['drug_name'],
                generic_name=drug_info.get('generic_name'),
                therapeutic_class=drug_info.get('therapeutic_class'),
                forecast_points=self._convert_forecast_points(
                    forecast, request.include_confidence_intervals
                ),
                total_predicted_demand=total_demand,
                average_daily_demand=avg_demand,
                trend_direction=forecaster.get_trend_direction(),
                confidence_score=forecaster.get_confidence_score()
            )
            
            drug_forecasts.append(drug_forecast)
        
        # Calculate total
        total_orders = sum(df.total_predicted_demand for df in drug_forecasts)
        
        pharmacy_forecast = PharmacyForecast(
            pharmacy_id=request.pharmacy_id,
            pharmacy_name=pharmacy_info['pharmacy_name'],
            drug_forecasts=drug_forecasts,
            total_predicted_orders=total_orders
        )
        
        return DemandForecastResponse(
            request_id=request_id,
            granularity=request.granularity,
            horizon_days=request.horizon_days,
            generated_at=datetime.utcnow(),
            forecast_start_date=datetime.utcnow().date() + timedelta(days=1),
            forecast_end_date=datetime.utcnow().date() + timedelta(days=request.horizon_days),
            pharmacy_forecasts=[pharmacy_forecast],
            drug_forecasts=None,
            model_version=ProphetForecaster.MODEL_VERSION,
            data_points_used=total_data_points,
            processing_time_seconds=0
        )
    
    async def _forecast_per_drug(
        self,
        request: DemandForecastRequest,
        request_id: UUID
    ) -> DemandForecastResponse:
        """Generate platform-wide forecast for a specific drug."""
        # Get drug info
        drug_info = self.pipeline.get_drug_info(request.drug_id)
        if not drug_info:
            raise ValueError(f"Drug not found: {request.drug_id}")
        
        # Get platform-wide data
        df = self.pipeline.get_demand_data_per_drug(request.drug_id)
        
        # Generate forecast
        forecaster = ProphetForecaster()
        forecaster.fit(df)
        forecast = forecaster.predict(request.horizon_days)
        
        total_demand, avg_demand = ProphetForecaster.calculate_total_demand(forecast)
        
        drug_forecast = DrugForecast(
            drug_id=request.drug_id,
            drug_name=drug_info['drug_name'],
            generic_name=drug_info.get('generic_name'),
            therapeutic_class=drug_info.get('therapeutic_class'),
            forecast_points=self._convert_forecast_points(
                forecast, request.include_confidence_intervals
            ),
            total_predicted_demand=total_demand,
            average_daily_demand=avg_demand,
            trend_direction=forecaster.get_trend_direction(),
            confidence_score=forecaster.get_confidence_score()
        )
        
        return DemandForecastResponse(
            request_id=request_id,
            granularity=request.granularity,
            horizon_days=request.horizon_days,
            generated_at=datetime.utcnow(),
            forecast_start_date=datetime.utcnow().date() + timedelta(days=1),
            forecast_end_date=datetime.utcnow().date() + timedelta(days=request.horizon_days),
            pharmacy_forecasts=None,
            drug_forecasts=[drug_forecast],
            model_version=ProphetForecaster.MODEL_VERSION,
            data_points_used=len(df),
            processing_time_seconds=0
        )
    
    async def _forecast_aggregate(
        self,
        request: DemandForecastRequest,
        request_id: UUID
    ) -> DemandForecastResponse:
        """Generate platform-wide aggregate forecast for all drugs."""
        # Get aggregate data for all drugs
        drug_data = self.pipeline.get_aggregate_demand_data()
        
        if not drug_data:
            logger.warning("No demand data found for aggregate forecast")
            return self._create_empty_response(request_id, request)
        
        drug_forecasts = []
        total_data_points = 0
        
        for drug_id, df in drug_data.items():
            total_data_points += len(df)
            
            drug_info = self.pipeline.get_drug_info(drug_id)
            if not drug_info:
                continue
            
            # Generate forecast
            forecaster = ProphetForecaster()
            forecaster.fit(df)
            forecast = forecaster.predict(request.horizon_days)
            
            total_demand, avg_demand = ProphetForecaster.calculate_total_demand(forecast)
            
            drug_forecast = DrugForecast(
                drug_id=drug_id,
                drug_name=drug_info['drug_name'],
                generic_name=drug_info.get('generic_name'),
                therapeutic_class=drug_info.get('therapeutic_class'),
                forecast_points=self._convert_forecast_points(
                    forecast, request.include_confidence_intervals
                ),
                total_predicted_demand=total_demand,
                average_daily_demand=avg_demand,
                trend_direction=forecaster.get_trend_direction(),
                confidence_score=forecaster.get_confidence_score()
            )
            
            drug_forecasts.append(drug_forecast)
        
        return DemandForecastResponse(
            request_id=request_id,
            granularity=request.granularity,
            horizon_days=request.horizon_days,
            generated_at=datetime.utcnow(),
            forecast_start_date=datetime.utcnow().date() + timedelta(days=1),
            forecast_end_date=datetime.utcnow().date() + timedelta(days=request.horizon_days),
            pharmacy_forecasts=None,
            drug_forecasts=drug_forecasts,
            model_version=ProphetForecaster.MODEL_VERSION,
            data_points_used=total_data_points,
            processing_time_seconds=0
        )
    
    async def generate_reorder_recommendations(
        self,
        request: ReorderRecommendationRequest
    ) -> ReorderRecommendationResponse:
        """
        Generate smart reorder recommendations based on forecasts.
        
        Args:
            request: ReorderRecommendationRequest
            
        Returns:
            ReorderRecommendationResponse with recommendations
        """
        logger.info(f"Generating reorder recommendations for pharmacy {request.pharmacy_id}")
        
        # Get pharmacy info
        pharmacy_info = self.pipeline.get_pharmacy_info(request.pharmacy_id)
        if not pharmacy_info:
            raise ValueError(f"Pharmacy not found: {request.pharmacy_id}")
        
        # Get current inventory
        inventory = self.pipeline.get_current_inventory(request.pharmacy_id)
        
        # Get demand forecasts for all drugs in inventory
        immediate_reorders = []
        upcoming_reorders = []
        total_reorder_value = Decimal('0')
        
        for item in inventory:
            drug_id = item['drug_id']
            current_stock = item['quantity_available']
            unit_price = item['unit_price']
            
            # Get demand data and forecast
            df = self.pipeline.get_demand_data_per_drug_pharmacy(
                request.pharmacy_id, drug_id
            )
            
            forecaster = ProphetForecaster()
            forecaster.fit(df)
            forecast = forecaster.predict(request.forecast_horizon)
            
            total_demand, avg_demand = ProphetForecaster.calculate_total_demand(forecast)
            
            # Calculate safety stock
            safety_stock = int(avg_demand * request.safety_stock_days)
            
            # Calculate reorder point (lead time demand + safety stock)
            lead_time_demand = avg_demand * request.lead_time_days
            reorder_point = lead_time_demand + safety_stock
            
            # Determine if reorder is needed
            days_until_stockout = None
            if avg_demand > 0:
                days_until_stockout = int(current_stock / avg_demand)
            
            # Calculate recommended reorder quantity
            # Target: cover forecast period + safety stock
            target_stock = total_demand + safety_stock
            reorder_quantity = max(0, int(target_stock - current_stock))
            
            if reorder_quantity > 0:
                reorder_item = ReorderItem(
                    drug_id=drug_id,
                    drug_name=item['drug_name'],
                    current_stock=current_stock,
                    predicted_demand=total_demand,
                    safety_stock=safety_stock,
                    reorder_quantity=reorder_quantity,
                    urgency=self._determine_urgency(current_stock, reorder_point, days_until_stockout),
                    days_until_stockout=days_until_stockout,
                    estimated_cost=Decimal(str(reorder_quantity * unit_price))
                )
                
                total_reorder_value += reorder_item.estimated_cost
                
                if reorder_item.urgency == 'immediate':
                    immediate_reorders.append(reorder_item)
                else:
                    upcoming_reorders.append(reorder_item)
        
        # Sort by urgency
        immediate_reorders.sort(key=lambda x: x.days_until_stockout or 0)
        upcoming_reorders.sort(key=lambda x: x.days_until_stockout or 999)
        
        # Generate summary
        summary = self._generate_reorder_summary(
            immediate_reorders, upcoming_reorders, total_reorder_value
        )
        
        return ReorderRecommendationResponse(
            pharmacy_id=request.pharmacy_id,
            pharmacy_name=pharmacy_info['pharmacy_name'],
            generated_at=datetime.utcnow(),
            forecast_horizon_days=request.forecast_horizon,
            immediate_reorders=immediate_reorders,
            upcoming_reorders=upcoming_reorders,
            total_reorder_value=total_reorder_value,
            summary=summary
        )
    
    def _determine_urgency(
        self,
        current_stock: int,
        reorder_point: float,
        days_until_stockout: Optional[int]
    ) -> str:
        """Determine reorder urgency."""
        if days_until_stockout is not None:
            if days_until_stockout <= 3:
                return 'immediate'
            elif days_until_stockout <= 7:
                return 'soon'
        
        if current_stock <= reorder_point:
            return 'immediate' if current_stock <= reorder_point * 0.5 else 'soon'
        
        return 'planned'
    
    def _generate_reorder_summary(
        self,
        immediate: list[ReorderItem],
        upcoming: list[ReorderItem],
        total_value: Decimal
    ) -> str:
        """Generate human-readable reorder summary."""
        parts = []
        
        if immediate:
            parts.append(f"{len(immediate)} items require immediate reorder")
        if upcoming:
            parts.append(f"{len(upcoming)} items should be reordered soon")
        
        if not parts:
            return "All inventory levels are adequate for the forecast period."
        
        summary = ". ".join(parts)
        summary += f". Total estimated reorder value: ${total_value:,.2f}."
        
        return summary
    
    def _convert_forecast_points(
        self,
        forecast,
        include_bounds: bool
    ) -> list[ForecastDataPoint]:
        """Convert Prophet forecast to ForecastDataPoint list."""
        points = []
        
        for _, row in forecast.iterrows():
            point = ForecastDataPoint(
                forecast_date=row['ds'].date() if hasattr(row['ds'], 'date') else row['ds'],
                predicted_quantity=round(float(row['yhat']), 2),
                lower_bound=round(float(row['yhat_lower']), 2) if include_bounds else None,
                upper_bound=round(float(row['yhat_upper']), 2) if include_bounds else None
            )
            points.append(point)
        
        return points
    
    def _create_empty_response(
        self,
        request_id: UUID,
        request: DemandForecastRequest,
        pharmacy_info: Optional[dict] = None
    ) -> DemandForecastResponse:
        """Create empty response when no data is available."""
        pharmacy_forecasts = None
        if pharmacy_info:
            pharmacy_forecasts = [PharmacyForecast(
                pharmacy_id=request.pharmacy_id,
                pharmacy_name=pharmacy_info['pharmacy_name'],
                drug_forecasts=[],
                total_predicted_orders=0
            )]
        
        return DemandForecastResponse(
            request_id=request_id,
            granularity=request.granularity,
            horizon_days=request.horizon_days,
            generated_at=datetime.utcnow(),
            forecast_start_date=datetime.utcnow().date() + timedelta(days=1),
            forecast_end_date=datetime.utcnow().date() + timedelta(days=request.horizon_days),
            pharmacy_forecasts=pharmacy_forecasts,
            drug_forecasts=[],
            model_version=ProphetForecaster.MODEL_VERSION,
            data_points_used=0,
            processing_time_seconds=0
        )
    
    async def _save_forecast(
        self,
        request: DemandForecastRequest,
        drug_forecast: DrugForecast,
        pharmacy_info: Optional[dict],
        forecaster: ProphetForecaster,
        data_points: int
    ) -> None:
        """Save forecast to database for caching and audit."""
        try:
            forecast_record = DemandForecastModel(
                pharmacy_id=request.pharmacy_id,
                drug_id=request.drug_id,
                granularity=request.granularity.value,
                horizon_days=request.horizon_days,
                forecast_start_date=datetime.utcnow().date() + timedelta(days=1),
                forecast_end_date=datetime.utcnow().date() + timedelta(days=request.horizon_days),
                forecast_data={
                    'points': [
                        {
                            'date': str(p.forecast_date),
                            'predicted': p.predicted_quantity,
                            'lower': p.lower_bound,
                            'upper': p.upper_bound
                        }
                        for p in drug_forecast.forecast_points
                    ]
                },
                total_predicted_demand=Decimal(str(drug_forecast.total_predicted_demand)),
                average_daily_demand=Decimal(str(drug_forecast.average_daily_demand)),
                trend_direction=drug_forecast.trend_direction,
                confidence_score=Decimal(str(drug_forecast.confidence_score)),
                model_version=ProphetForecaster.MODEL_VERSION,
                training_data_points=data_points,
                training_period_start=None,
                training_period_end=datetime.utcnow().date()
            )
            
            self.session.add(forecast_record)
            self.session.commit()
            
            logger.info(f"Saved forecast record: {forecast_record.id}")
            
        except Exception as e:
            logger.error(f"Error saving forecast to database: {str(e)}")
            # Don't fail the request if saving fails

