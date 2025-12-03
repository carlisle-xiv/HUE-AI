import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

import pandas as pd
import numpy as np
from sqlmodel import Session, select, and_

from src.models.pharmacy import DrugOrder, DrugOrderItem, Pharmacy, PharmacyInventory
from src.models.reference import PharmacyCode

from ..schemas import (
    AnomalyDetectionResponse,
    DemandAnomaly,
    AnomalyType,
)
from ..demand_forecasting.data_pipeline import DemandDataPipeline
from ..demand_forecasting.prophet_forecaster import ProphetForecaster
from ..demand_forecasting.models import DemandAnomaly as DemandAnomalyModel

# Configure logging
logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects demand anomalies using Prophet's uncertainty intervals
    and statistical methods.
    """
    
    # Thresholds for anomaly detection
    SPIKE_THRESHOLD = 2.0  # Standard deviations above mean
    DROP_THRESHOLD = -1.5  # Standard deviations below mean
    MIN_DEVIATION_PERCENT = 50  # Minimum percentage deviation to flag
    
    def __init__(self, session: Session):
        self.session = session
        self.pipeline = DemandDataPipeline(session)
    
    async def detect_anomalies(
        self,
        pharmacy_id: Optional[UUID] = None,
        drug_id: Optional[UUID] = None,
        days_back: int = 30
    ) -> AnomalyDetectionResponse:
        """
        Detect demand anomalies in historical data.
        
        Args:
            pharmacy_id: Optional pharmacy filter
            drug_id: Optional drug filter
            days_back: Days of history to analyze
            
        Returns:
            AnomalyDetectionResponse with detected anomalies
        """
        logger.info(f"Detecting anomalies for past {days_back} days")
        
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days_back)
        
        anomalies = []
        
        if drug_id and pharmacy_id:
            # Specific drug at specific pharmacy
            drug_anomalies = await self._detect_drug_pharmacy_anomalies(
                pharmacy_id, drug_id, days_back
            )
            anomalies.extend(drug_anomalies)
        elif pharmacy_id:
            # All drugs at a pharmacy
            pharmacy_anomalies = await self._detect_pharmacy_anomalies(
                pharmacy_id, days_back
            )
            anomalies.extend(pharmacy_anomalies)
        elif drug_id:
            # Specific drug platform-wide
            drug_anomalies = await self._detect_drug_anomalies(drug_id, days_back)
            anomalies.extend(drug_anomalies)
        else:
            # Platform-wide detection
            platform_anomalies = await self._detect_platform_anomalies(days_back)
            anomalies.extend(platform_anomalies)
        
        # Sort by severity and date
        anomalies.sort(key=lambda x: (
            -self._severity_priority(x.severity),
            x.anomaly_date
        ), reverse=True)
        
        # Summarize by type
        summary = self._summarize_anomalies(anomalies)
        
        logger.info(f"Detected {len(anomalies)} anomalies")
        
        return AnomalyDetectionResponse(
            analysis_period_start=start_date,
            analysis_period_end=end_date,
            total_anomalies_detected=len(anomalies),
            anomalies=anomalies,
            summary_by_type=summary
        )
    
    async def _detect_drug_pharmacy_anomalies(
        self,
        pharmacy_id: UUID,
        drug_id: UUID,
        days_back: int
    ) -> list[DemandAnomaly]:
        """Detect anomalies for specific drug at specific pharmacy."""
        # Get historical data
        df = self.pipeline.get_demand_data_per_drug_pharmacy(
            pharmacy_id, drug_id, days_back + 60  # Extra data for model training
        )
        
        if df.empty or len(df) < 30:
            return []
        
        drug_info = self.pipeline.get_drug_info(drug_id)
        
        return self._analyze_for_anomalies(
            df, days_back, pharmacy_id, drug_id, drug_info
        )
    
    async def _detect_pharmacy_anomalies(
        self,
        pharmacy_id: UUID,
        days_back: int
    ) -> list[DemandAnomaly]:
        """Detect anomalies for all drugs at a pharmacy."""
        # Get data for all drugs
        drug_data = self.pipeline.get_demand_data_per_pharmacy(pharmacy_id, days_back + 60)
        
        anomalies = []
        for drug_id, df in drug_data.items():
            if len(df) < 30:
                continue
            
            drug_info = self.pipeline.get_drug_info(drug_id)
            drug_anomalies = self._analyze_for_anomalies(
                df, days_back, pharmacy_id, drug_id, drug_info
            )
            anomalies.extend(drug_anomalies)
        
        return anomalies
    
    async def _detect_drug_anomalies(
        self,
        drug_id: UUID,
        days_back: int
    ) -> list[DemandAnomaly]:
        """Detect anomalies for specific drug platform-wide."""
        df = self.pipeline.get_demand_data_per_drug(drug_id, days_back + 60)
        
        if df.empty or len(df) < 30:
            return []
        
        drug_info = self.pipeline.get_drug_info(drug_id)
        
        return self._analyze_for_anomalies(
            df, days_back, None, drug_id, drug_info
        )
    
    async def _detect_platform_anomalies(
        self,
        days_back: int
    ) -> list[DemandAnomaly]:
        """Detect anomalies across all drugs platform-wide."""
        # Get aggregate data
        drug_data = self.pipeline.get_aggregate_demand_data(days_back + 60)
        
        anomalies = []
        # Limit to top drugs by volume to avoid excessive processing
        sorted_drugs = sorted(
            drug_data.items(),
            key=lambda x: x[1]['y'].sum() if not x[1].empty else 0,
            reverse=True
        )[:50]  # Top 50 drugs
        
        for drug_id, df in sorted_drugs:
            if len(df) < 30:
                continue
            
            drug_info = self.pipeline.get_drug_info(drug_id)
            drug_anomalies = self._analyze_for_anomalies(
                df, days_back, None, drug_id, drug_info
            )
            anomalies.extend(drug_anomalies)
        
        return anomalies
    
    def _analyze_for_anomalies(
        self,
        df: pd.DataFrame,
        days_back: int,
        pharmacy_id: Optional[UUID],
        drug_id: Optional[UUID],
        drug_info: Optional[dict]
    ) -> list[DemandAnomaly]:
        """
        Analyze a time series for anomalies using multiple methods.
        """
        anomalies = []
        
        # Method 1: Prophet-based detection
        prophet_anomalies = self._detect_with_prophet(
            df, days_back, pharmacy_id, drug_id, drug_info
        )
        anomalies.extend(prophet_anomalies)
        
        # Method 2: Statistical detection (Z-score based)
        stat_anomalies = self._detect_with_statistics(
            df, days_back, pharmacy_id, drug_id, drug_info
        )
        
        # Add statistical anomalies that weren't caught by Prophet
        existing_dates = {(a.anomaly_date, a.anomaly_type) for a in anomalies}
        for anomaly in stat_anomalies:
            if (anomaly.anomaly_date, anomaly.anomaly_type) not in existing_dates:
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_with_prophet(
        self,
        df: pd.DataFrame,
        days_back: int,
        pharmacy_id: Optional[UUID],
        drug_id: Optional[UUID],
        drug_info: Optional[dict]
    ) -> list[DemandAnomaly]:
        """Detect anomalies using Prophet's uncertainty intervals."""
        try:
            # Train Prophet on historical data
            forecaster = ProphetForecaster(interval_width=0.95)
            forecaster.fit(df)
            
            # Get Prophet's anomalies
            raw_anomalies = forecaster.detect_anomalies()
            
            # Filter to analysis period
            cutoff_date = datetime.utcnow().date() - timedelta(days=days_back)
            
            anomalies = []
            for raw in raw_anomalies:
                anomaly_date = raw['date']
                if hasattr(anomaly_date, 'date'):
                    anomaly_date = anomaly_date.date()
                
                if anomaly_date < cutoff_date:
                    continue
                
                anomaly = self._create_anomaly(
                    anomaly_date=anomaly_date,
                    anomaly_type=AnomalyType.SPIKE if raw['type'] == 'spike' else AnomalyType.DROP,
                    expected=raw['expected'],
                    actual=raw['actual'],
                    deviation_pct=raw['deviation_percentage'],
                    pharmacy_id=pharmacy_id,
                    drug_id=drug_id,
                    drug_info=drug_info
                )
                
                if anomaly:
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.warning(f"Prophet anomaly detection failed: {str(e)}")
            return []
    
    def _detect_with_statistics(
        self,
        df: pd.DataFrame,
        days_back: int,
        pharmacy_id: Optional[UUID],
        drug_id: Optional[UUID],
        drug_info: Optional[dict]
    ) -> list[DemandAnomaly]:
        """Detect anomalies using statistical methods (Z-score)."""
        try:
            df = df.copy()
            df['ds'] = pd.to_datetime(df['ds'])
            
            # Calculate rolling statistics
            df['rolling_mean'] = df['y'].rolling(window=14, min_periods=7).mean()
            df['rolling_std'] = df['y'].rolling(window=14, min_periods=7).std()
            
            # Calculate Z-score
            df['z_score'] = (df['y'] - df['rolling_mean']) / (df['rolling_std'] + 0.001)
            
            # Filter to analysis period
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            recent_df = df[df['ds'] >= cutoff_date]
            
            anomalies = []
            for _, row in recent_df.iterrows():
                if pd.isna(row['z_score']) or pd.isna(row['rolling_mean']):
                    continue
                
                # Check for spike
                if row['z_score'] > self.SPIKE_THRESHOLD:
                    deviation_pct = (row['y'] - row['rolling_mean']) / (row['rolling_mean'] + 0.001) * 100
                    if abs(deviation_pct) >= self.MIN_DEVIATION_PERCENT:
                        anomaly = self._create_anomaly(
                            anomaly_date=row['ds'].date(),
                            anomaly_type=AnomalyType.SPIKE,
                            expected=row['rolling_mean'],
                            actual=row['y'],
                            deviation_pct=deviation_pct,
                            deviation_sigma=row['z_score'],
                            pharmacy_id=pharmacy_id,
                            drug_id=drug_id,
                            drug_info=drug_info
                        )
                        if anomaly:
                            anomalies.append(anomaly)
                
                # Check for drop
                elif row['z_score'] < self.DROP_THRESHOLD:
                    deviation_pct = (row['y'] - row['rolling_mean']) / (row['rolling_mean'] + 0.001) * 100
                    if abs(deviation_pct) >= self.MIN_DEVIATION_PERCENT / 2:
                        anomaly = self._create_anomaly(
                            anomaly_date=row['ds'].date(),
                            anomaly_type=AnomalyType.DROP,
                            expected=row['rolling_mean'],
                            actual=row['y'],
                            deviation_pct=deviation_pct,
                            deviation_sigma=row['z_score'],
                            pharmacy_id=pharmacy_id,
                            drug_id=drug_id,
                            drug_info=drug_info
                        )
                        if anomaly:
                            anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.warning(f"Statistical anomaly detection failed: {str(e)}")
            return []
    
    def _create_anomaly(
        self,
        anomaly_date: date,
        anomaly_type: AnomalyType,
        expected: float,
        actual: float,
        deviation_pct: float,
        pharmacy_id: Optional[UUID],
        drug_id: Optional[UUID],
        drug_info: Optional[dict],
        deviation_sigma: Optional[float] = None
    ) -> Optional[DemandAnomaly]:
        """Create a DemandAnomaly object with analysis."""
        # Determine severity
        abs_deviation = abs(deviation_pct)
        if abs_deviation >= 200:
            severity = 'critical'
        elif abs_deviation >= 100:
            severity = 'high'
        elif abs_deviation >= 50:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Generate possible causes
        possible_causes = self._generate_possible_causes(anomaly_type, deviation_pct, drug_info)
        
        # Generate recommended actions
        recommended_actions = self._generate_recommended_actions(
            anomaly_type, severity, drug_info
        )
        
        return DemandAnomaly(
            anomaly_id=uuid4(),
            detected_at=datetime.utcnow(),
            anomaly_type=anomaly_type,
            pharmacy_id=pharmacy_id,
            drug_id=drug_id,
            drug_name=drug_info.get('drug_name') if drug_info else None,
            anomaly_date=anomaly_date,
            expected_demand=round(expected, 2),
            actual_demand=round(actual, 2),
            deviation_percentage=round(deviation_pct, 2),
            severity=severity,
            possible_causes=possible_causes,
            recommended_actions=recommended_actions
        )
    
    def _generate_possible_causes(
        self,
        anomaly_type: AnomalyType,
        deviation_pct: float,
        drug_info: Optional[dict]
    ) -> list[str]:
        """Generate possible causes for the anomaly."""
        causes = []
        
        if anomaly_type == AnomalyType.SPIKE:
            causes.append("Seasonal disease outbreak or epidemic")
            causes.append("Promotional campaign or special pricing")
            causes.append("Stock-up behavior before anticipated shortage")
            
            if drug_info and drug_info.get('therapeutic_class'):
                therapeutic_class = drug_info['therapeutic_class'].lower()
                if 'antibiotic' in therapeutic_class or 'antimalarial' in therapeutic_class:
                    causes.insert(0, "Disease outbreak in the region")
                elif 'pain' in therapeutic_class or 'analgesic' in therapeutic_class:
                    causes.insert(0, "Increased general illness or injury reports")
        
        elif anomaly_type == AnomalyType.DROP:
            causes.append("Stock-out at pharmacy")
            causes.append("Supply chain disruption")
            causes.append("Product recall or safety concern")
            causes.append("Data entry error or system issue")
            causes.append("Competition from alternative products")
        
        return causes[:5]  # Limit to 5 causes
    
    def _generate_recommended_actions(
        self,
        anomaly_type: AnomalyType,
        severity: str,
        drug_info: Optional[dict]
    ) -> list[str]:
        """Generate recommended actions based on anomaly."""
        actions = []
        
        if anomaly_type == AnomalyType.SPIKE:
            if severity in ['critical', 'high']:
                actions.append("Verify stock levels and consider emergency reorder")
                actions.append("Investigate if disease outbreak is occurring")
                actions.append("Check for bulk orders or unusual purchasing patterns")
            else:
                actions.append("Monitor inventory levels closely")
                actions.append("Review if promotion or marketing campaign is active")
        
        elif anomaly_type == AnomalyType.DROP:
            if severity in ['critical', 'high']:
                actions.append("Immediately verify inventory availability")
                actions.append("Check for supply chain issues or product recalls")
                actions.append("Verify data integrity in order system")
            else:
                actions.append("Monitor for continued drop in demand")
                actions.append("Review competitor activity")
        
        return actions
    
    def _summarize_anomalies(self, anomalies: list[DemandAnomaly]) -> dict[str, int]:
        """Summarize anomalies by type."""
        summary = {
            'spike': 0,
            'drop': 0,
            'trend_change': 0
        }
        
        for anomaly in anomalies:
            summary[anomaly.anomaly_type.value] += 1
        
        return summary
    
    def _severity_priority(self, severity: str) -> int:
        """Get priority number for severity."""
        priorities = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        return priorities.get(severity, 0)
    
    async def save_anomalies(self, anomalies: list[DemandAnomaly]) -> None:
        """Save detected anomalies to database."""
        try:
            for anomaly in anomalies:
                record = DemandAnomalyModel(
                    pharmacy_id=anomaly.pharmacy_id,
                    drug_id=anomaly.drug_id,
                    anomaly_type=anomaly.anomaly_type.value,
                    anomaly_date=anomaly.anomaly_date,
                    expected_demand=Decimal(str(anomaly.expected_demand)),
                    actual_demand=Decimal(str(anomaly.actual_demand)),
                    deviation_percentage=Decimal(str(anomaly.deviation_percentage)),
                    severity=anomaly.severity,
                    possible_causes=anomaly.possible_causes,
                    recommended_actions=anomaly.recommended_actions,
                    detected_at=anomaly.detected_at
                )
                
                self.session.add(record)
            
            self.session.commit()
            logger.info(f"Saved {len(anomalies)} anomalies to database")
            
        except Exception as e:
            logger.error(f"Error saving anomalies: {str(e)}")

