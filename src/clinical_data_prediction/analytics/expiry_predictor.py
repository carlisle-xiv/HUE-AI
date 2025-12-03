import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, and_

from src.models.pharmacy import Pharmacy, PharmacyInventory
from src.models.reference import PharmacyCode

from ..schemas import (
    ExpiryRiskRequest,
    ExpiryRiskResponse,
    ExpiryRiskItem,
    ExpiryRiskLevel,
)
from ..demand_forecasting.data_pipeline import DemandDataPipeline
from ..demand_forecasting.prophet_forecaster import ProphetForecaster

# Configure logging
logger = logging.getLogger(__name__)


class ExpiryPredictor:
    """
    Predicts which drugs are at risk of expiring before being sold.
    Compares forecasted demand with current inventory and expiry dates.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.pipeline = DemandDataPipeline(session)
    
    async def analyze_expiry_risk(
        self,
        request: ExpiryRiskRequest
    ) -> ExpiryRiskResponse:
        """
        Analyze inventory for expiry risk.
        
        Args:
            request: ExpiryRiskRequest with filters and parameters
            
        Returns:
            ExpiryRiskResponse with risk items and summary
        """
        logger.info(f"Analyzing expiry risk for {request.days_ahead} days ahead")
        
        # Get inventory items with expiry dates
        inventory_items = self._get_expiring_inventory(
            request.pharmacy_id,
            request.drug_id,
            request.days_ahead
        )
        
        if not inventory_items:
            return ExpiryRiskResponse(
                analysis_date=datetime.utcnow(),
                total_items_at_risk=0,
                total_potential_loss=Decimal('0'),
                risk_items=[],
                summary_by_risk_level={'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            )
        
        risk_items = []
        total_potential_loss = Decimal('0')
        risk_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        
        for item in inventory_items:
            risk_item = await self._analyze_item_risk(item, request.days_ahead)
            
            if risk_item and self._meets_minimum_risk(risk_item.risk_level, request.min_risk_level):
                risk_items.append(risk_item)
                total_potential_loss += risk_item.potential_loss_value
                risk_counts[risk_item.risk_level.value] += 1
        
        # Sort by risk level (critical first) then by days until expiry
        risk_items.sort(key=lambda x: (
            -self._risk_level_priority(x.risk_level),
            x.days_until_expiry
        ))
        
        logger.info(f"Found {len(risk_items)} items at risk of expiry")
        
        return ExpiryRiskResponse(
            analysis_date=datetime.utcnow(),
            total_items_at_risk=len(risk_items),
            total_potential_loss=total_potential_loss,
            risk_items=risk_items,
            summary_by_risk_level=risk_counts
        )
    
    def _get_expiring_inventory(
        self,
        pharmacy_id: Optional[UUID],
        drug_id: Optional[UUID],
        days_ahead: int
    ) -> list[dict]:
        """Get inventory items with expiry dates within the analysis window."""
        end_date = datetime.utcnow().date() + timedelta(days=days_ahead)
        
        # Build query
        stmt = (
            select(PharmacyInventory, PharmacyCode, Pharmacy)
            .join(PharmacyCode, PharmacyInventory.pharmacy_code_id == PharmacyCode.id)
            .join(Pharmacy, PharmacyInventory.pharmacy_id == Pharmacy.id)
            .where(
                and_(
                    PharmacyInventory.quantity_available > 0,
                    PharmacyInventory.expiry_date != None,
                    PharmacyInventory.expiry_date <= end_date,
                    PharmacyInventory.expiry_date >= datetime.utcnow().date()
                )
            )
        )
        
        if pharmacy_id:
            stmt = stmt.where(PharmacyInventory.pharmacy_id == pharmacy_id)
        
        if drug_id:
            stmt = stmt.where(PharmacyInventory.pharmacy_code_id == drug_id)
        
        results = self.session.exec(stmt).all()
        
        items = []
        for inventory, drug, pharmacy in results:
            items.append({
                'inventory_id': inventory.id,
                'pharmacy_id': pharmacy.id,
                'pharmacy_name': pharmacy.name,
                'drug_id': drug.id,
                'drug_name': drug.drug_name,
                'quantity': inventory.quantity_available,
                'unit_price': inventory.unit_price,
                'expiry_date': inventory.expiry_date
            })
        
        return items
    
    async def _analyze_item_risk(
        self,
        item: dict,
        analysis_days: int
    ) -> Optional[ExpiryRiskItem]:
        """Analyze expiry risk for a single inventory item."""
        expiry_date = item['expiry_date']
        today = datetime.utcnow().date()
        days_until_expiry = (expiry_date - today).days
        
        if days_until_expiry <= 0:
            # Already expired
            return ExpiryRiskItem(
                pharmacy_id=item['pharmacy_id'],
                pharmacy_name=item['pharmacy_name'],
                drug_id=item['drug_id'],
                drug_name=item['drug_name'],
                current_quantity=item['quantity'],
                expiry_date=expiry_date,
                days_until_expiry=days_until_expiry,
                predicted_demand_until_expiry=0,
                estimated_waste_quantity=float(item['quantity']),
                risk_level=ExpiryRiskLevel.CRITICAL,
                recommended_action="EXPIRED - Remove from inventory immediately",
                potential_loss_value=Decimal(str(item['quantity'] * float(item['unit_price'])))
            )
        
        # Get demand forecast until expiry date
        try:
            df = self.pipeline.get_demand_data_per_drug_pharmacy(
                item['pharmacy_id'],
                item['drug_id']
            )
            
            forecaster = ProphetForecaster()
            forecaster.fit(df)
            forecast = forecaster.predict(days_until_expiry)
            
            predicted_demand, _ = ProphetForecaster.calculate_total_demand(forecast)
            
        except Exception as e:
            logger.warning(f"Could not forecast demand for item: {str(e)}")
            predicted_demand = 0
        
        # Calculate estimated waste
        estimated_waste = max(0, item['quantity'] - predicted_demand)
        waste_percentage = (estimated_waste / item['quantity']) * 100 if item['quantity'] > 0 else 100
        
        # Determine risk level
        risk_level = self._calculate_risk_level(
            days_until_expiry,
            waste_percentage,
            item['quantity']
        )
        
        # Generate recommendation
        recommended_action = self._generate_recommendation(
            risk_level,
            days_until_expiry,
            estimated_waste,
            item['quantity']
        )
        
        potential_loss = Decimal(str(estimated_waste * float(item['unit_price'])))
        
        return ExpiryRiskItem(
            pharmacy_id=item['pharmacy_id'],
            pharmacy_name=item['pharmacy_name'],
            drug_id=item['drug_id'],
            drug_name=item['drug_name'],
            current_quantity=item['quantity'],
            expiry_date=expiry_date,
            days_until_expiry=days_until_expiry,
            predicted_demand_until_expiry=predicted_demand,
            estimated_waste_quantity=estimated_waste,
            risk_level=risk_level,
            recommended_action=recommended_action,
            potential_loss_value=potential_loss
        )
    
    def _calculate_risk_level(
        self,
        days_until_expiry: int,
        waste_percentage: float,
        quantity: int
    ) -> ExpiryRiskLevel:
        """Calculate risk level based on expiry timeline and waste percentage."""
        # Critical: Expiring very soon with significant waste
        if days_until_expiry <= 7:
            if waste_percentage > 30:
                return ExpiryRiskLevel.CRITICAL
            elif waste_percentage > 10:
                return ExpiryRiskLevel.HIGH
        
        # High: Expiring within a month with high waste
        if days_until_expiry <= 30:
            if waste_percentage > 50:
                return ExpiryRiskLevel.CRITICAL
            elif waste_percentage > 30:
                return ExpiryRiskLevel.HIGH
            elif waste_percentage > 10:
                return ExpiryRiskLevel.MEDIUM
        
        # Medium: Expiring within 60 days with moderate waste
        if days_until_expiry <= 60:
            if waste_percentage > 50:
                return ExpiryRiskLevel.HIGH
            elif waste_percentage > 20:
                return ExpiryRiskLevel.MEDIUM
        
        # Low: Further out or low waste percentage
        if waste_percentage > 30:
            return ExpiryRiskLevel.MEDIUM
        elif waste_percentage > 10:
            return ExpiryRiskLevel.LOW
        
        return ExpiryRiskLevel.LOW
    
    def _generate_recommendation(
        self,
        risk_level: ExpiryRiskLevel,
        days_until_expiry: int,
        estimated_waste: float,
        current_quantity: int
    ) -> str:
        """Generate actionable recommendation based on risk assessment."""
        waste_percentage = (estimated_waste / current_quantity) * 100 if current_quantity > 0 else 100
        
        if risk_level == ExpiryRiskLevel.CRITICAL:
            if days_until_expiry <= 7:
                return f"URGENT: Consider markdown pricing or transfer to higher-demand location. {int(estimated_waste)} units at risk of expiry within {days_until_expiry} days."
            else:
                return f"CRITICAL: {waste_percentage:.0f}% of stock likely to expire. Implement aggressive sales strategy or arrange returns/transfers."
        
        elif risk_level == ExpiryRiskLevel.HIGH:
            if days_until_expiry <= 30:
                return f"HIGH PRIORITY: {int(estimated_waste)} units may expire. Consider promotional pricing or transfer to nearby locations with higher demand."
            else:
                return f"Review inventory levels. Consider reducing future orders and implementing promotional pricing."
        
        elif risk_level == ExpiryRiskLevel.MEDIUM:
            return f"Monitor closely. Consider slight promotional pricing for items expiring in {days_until_expiry} days."
        
        else:  # LOW
            return f"Low risk - continue monitoring. {days_until_expiry} days until expiry with adequate predicted demand."
    
    def _meets_minimum_risk(
        self,
        item_risk: ExpiryRiskLevel,
        min_risk: ExpiryRiskLevel
    ) -> bool:
        """Check if item meets minimum risk threshold."""
        priority = self._risk_level_priority
        return priority(item_risk) >= priority(min_risk)
    
    def _risk_level_priority(self, level: ExpiryRiskLevel) -> int:
        """Get priority number for risk level (higher = more severe)."""
        priorities = {
            ExpiryRiskLevel.LOW: 1,
            ExpiryRiskLevel.MEDIUM: 2,
            ExpiryRiskLevel.HIGH: 3,
            ExpiryRiskLevel.CRITICAL: 4
        }
        return priorities.get(level, 0)

