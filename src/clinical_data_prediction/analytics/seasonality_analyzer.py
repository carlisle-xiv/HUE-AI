import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

import pandas as pd
import numpy as np
from sqlmodel import Session

from src.models.reference import PharmacyCode

from ..schemas import (
    SeasonalityResponse,
    SeasonalityPattern as SeasonalityPatternSchema,
    SeasonalPattern,
)
from ..demand_forecasting.data_pipeline import DemandDataPipeline
from ..demand_forecasting.models import SeasonalityPattern as SeasonalityPatternModel

# Configure logging
logger = logging.getLogger(__name__)

# Ghana disease seasons (approximate)
GHANA_DISEASE_SEASONS = {
    'malaria': {
        'peak_months': [5, 6, 7, 8, 9, 10],  # Rainy season
        'drugs': ['artemether', 'lumefantrine', 'artesunate', 'chloroquine', 'quinine']
    },
    'respiratory': {
        'peak_months': [11, 12, 1, 2],  # Harmattan/dry season
        'drugs': ['amoxicillin', 'azithromycin', 'cough', 'paracetamol', 'ibuprofen']
    },
    'diarrhea': {
        'peak_months': [3, 4, 5],  # Hot/early rainy season
        'drugs': ['ors', 'zinc', 'metronidazole', 'ciprofloxacin']
    },
    'skin_infections': {
        'peak_months': [6, 7, 8, 9],  # Rainy season humidity
        'drugs': ['clotrimazole', 'miconazole', 'fluconazole', 'antifungal']
    }
}


class SeasonalityAnalyzer:
    """
    Analyzes demand patterns to detect seasonality.
    Identifies weekly, monthly, and disease-season patterns.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.pipeline = DemandDataPipeline(session)
    
    async def analyze_seasonality(
        self,
        drug_id: UUID,
        analysis_days: int = 365
    ) -> SeasonalityResponse:
        """
        Analyze demand patterns for a specific drug.
        
        Args:
            drug_id: Drug/pharmacy_code UUID
            analysis_days: Days of historical data to analyze
            
        Returns:
            SeasonalityResponse with detected patterns
        """
        logger.info(f"Analyzing seasonality for drug {drug_id}")
        
        # Get drug info
        drug_info = self.pipeline.get_drug_info(drug_id)
        if not drug_info:
            raise ValueError(f"Drug not found: {drug_id}")
        
        # Get historical demand data
        df = self.pipeline.get_demand_data_per_drug(drug_id, analysis_days)
        
        if df.empty or df['y'].sum() == 0:
            return SeasonalityResponse(
                drug_id=drug_id,
                drug_name=drug_info['drug_name'],
                analysis_period_days=analysis_days,
                patterns_detected=[],
                has_strong_seasonality=False,
                recommendations=["Insufficient data for seasonality analysis"]
            )
        
        # Detect various patterns
        patterns = []
        
        # Weekly pattern
        weekly_pattern = self._analyze_weekly_pattern(df)
        if weekly_pattern:
            patterns.append(weekly_pattern)
        
        # Monthly pattern
        monthly_pattern = self._analyze_monthly_pattern(df)
        if monthly_pattern:
            patterns.append(monthly_pattern)
        
        # Disease season pattern (Ghana-specific)
        disease_pattern = self._analyze_disease_season(df, drug_info['drug_name'])
        if disease_pattern:
            patterns.append(disease_pattern)
        
        # Determine if strong seasonality exists
        has_strong = any(p.strength > 0.5 for p in patterns)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            patterns, drug_info['drug_name'], df
        )
        
        # Save patterns to database
        await self._save_patterns(drug_id, patterns, analysis_days, df)
        
        return SeasonalityResponse(
            drug_id=drug_id,
            drug_name=drug_info['drug_name'],
            analysis_period_days=analysis_days,
            patterns_detected=patterns,
            has_strong_seasonality=has_strong,
            recommendations=recommendations
        )
    
    def _analyze_weekly_pattern(self, df: pd.DataFrame) -> Optional[SeasonalityPatternSchema]:
        """Analyze weekly demand patterns (weekday vs weekend)."""
        if len(df) < 14:  # Need at least 2 weeks
            return None
        
        try:
            df = df.copy()
            df['ds'] = pd.to_datetime(df['ds'])
            df['weekday'] = df['ds'].dt.day_name()
            df['is_weekend'] = df['ds'].dt.dayofweek >= 5
            
            # Calculate average by day of week
            daily_avg = df.groupby('weekday')['y'].mean()
            
            # Calculate strength (coefficient of variation)
            overall_mean = df['y'].mean()
            if overall_mean == 0:
                return None
            
            cv = daily_avg.std() / overall_mean
            strength = min(cv * 2, 1.0)  # Scale to 0-1
            
            if strength < 0.1:
                return None  # No significant weekly pattern
            
            # Find peak and low days
            peak_days = daily_avg.nlargest(2).index.tolist()
            low_days = daily_avg.nsmallest(2).index.tolist()
            
            # Weekend vs weekday comparison
            weekday_avg = df[~df['is_weekend']]['y'].mean()
            weekend_avg = df[df['is_weekend']]['y'].mean()
            
            if weekday_avg > weekend_avg * 1.2:
                description = "Higher demand on weekdays, particularly on " + " and ".join(peak_days[:2])
            elif weekend_avg > weekday_avg * 1.2:
                description = "Higher demand on weekends"
            else:
                description = f"Demand varies throughout the week. Peak days: {', '.join(peak_days[:2])}"
            
            return SeasonalityPatternSchema(
                pattern_type=SeasonalPattern.WEEKLY,
                strength=round(strength, 3),
                peak_periods=peak_days,
                low_periods=low_days,
                description=description
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing weekly pattern: {str(e)}")
            return None
    
    def _analyze_monthly_pattern(self, df: pd.DataFrame) -> Optional[SeasonalityPatternSchema]:
        """Analyze monthly demand patterns (beginning vs end of month)."""
        if len(df) < 60:  # Need at least 2 months
            return None
        
        try:
            df = df.copy()
            df['ds'] = pd.to_datetime(df['ds'])
            df['day_of_month'] = df['ds'].dt.day
            df['month_period'] = df['day_of_month'].apply(self._categorize_month_period)
            
            # Calculate average by period
            period_avg = df.groupby('month_period')['y'].mean()
            
            # Calculate strength
            overall_mean = df['y'].mean()
            if overall_mean == 0:
                return None
            
            cv = period_avg.std() / overall_mean
            strength = min(cv * 3, 1.0)  # Scale to 0-1
            
            if strength < 0.1:
                return None
            
            # Determine peak and low periods
            peak_period = period_avg.idxmax()
            low_period = period_avg.idxmin()
            
            # Generate description
            if peak_period in ['beginning', 'early']:
                description = "Higher demand at the beginning of the month (payday effect)"
            elif peak_period == 'end':
                description = "Higher demand at the end of the month"
            else:
                description = f"Demand peaks during {peak_period} of the month"
            
            return SeasonalityPatternSchema(
                pattern_type=SeasonalPattern.MONTHLY,
                strength=round(strength, 3),
                peak_periods=[peak_period],
                low_periods=[low_period],
                description=description
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing monthly pattern: {str(e)}")
            return None
    
    def _categorize_month_period(self, day: int) -> str:
        """Categorize day of month into period."""
        if day <= 7:
            return 'beginning'
        elif day <= 14:
            return 'early'
        elif day <= 21:
            return 'mid'
        else:
            return 'end'
    
    def _analyze_disease_season(
        self,
        df: pd.DataFrame,
        drug_name: str
    ) -> Optional[SeasonalityPatternSchema]:
        """Analyze disease-season patterns based on Ghana climate."""
        if len(df) < 180:  # Need at least 6 months
            return None
        
        try:
            df = df.copy()
            df['ds'] = pd.to_datetime(df['ds'])
            df['month'] = df['ds'].dt.month
            
            # Check which disease category this drug belongs to
            drug_name_lower = drug_name.lower()
            matched_season = None
            
            for season_name, season_info in GHANA_DISEASE_SEASONS.items():
                for keyword in season_info['drugs']:
                    if keyword in drug_name_lower:
                        matched_season = (season_name, season_info)
                        break
                if matched_season:
                    break
            
            # Calculate monthly averages
            monthly_avg = df.groupby('month')['y'].mean()
            
            # Calculate overall seasonality strength
            overall_mean = df['y'].mean()
            if overall_mean == 0:
                return None
            
            cv = monthly_avg.std() / overall_mean
            strength = min(cv * 2, 1.0)
            
            if strength < 0.15:
                return None
            
            # Find peak and low months
            peak_months = monthly_avg.nlargest(3).index.tolist()
            low_months = monthly_avg.nsmallest(3).index.tolist()
            
            month_names = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April',
                5: 'May', 6: 'June', 7: 'July', 8: 'August',
                9: 'September', 10: 'October', 11: 'November', 12: 'December'
            }
            
            peak_period_names = [month_names[m] for m in peak_months]
            low_period_names = [month_names[m] for m in low_months]
            
            # Generate description based on matched season or general pattern
            if matched_season:
                season_name, season_info = matched_season
                expected_peaks = season_info['peak_months']
                actual_match = len(set(peak_months) & set(expected_peaks)) >= 2
                
                if actual_match:
                    description = f"Matches {season_name.replace('_', ' ')} season pattern in Ghana. "
                    description += f"Peak demand in {', '.join(peak_period_names[:2])}"
                else:
                    description = f"Yearly pattern detected. Peak months: {', '.join(peak_period_names[:2])}"
            else:
                description = f"Yearly seasonal pattern. Peak demand in {', '.join(peak_period_names[:2])}"
            
            return SeasonalityPatternSchema(
                pattern_type=SeasonalPattern.DISEASE_SEASON if matched_season else SeasonalPattern.YEARLY,
                strength=round(strength, 3),
                peak_periods=peak_period_names,
                low_periods=low_period_names,
                description=description
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing disease season: {str(e)}")
            return None
    
    def _generate_recommendations(
        self,
        patterns: list[SeasonalityPatternSchema],
        drug_name: str,
        df: pd.DataFrame
    ) -> list[str]:
        """Generate stock recommendations based on detected patterns."""
        recommendations = []
        
        if not patterns:
            recommendations.append(
                "No strong seasonal patterns detected. Maintain steady inventory levels."
            )
            return recommendations
        
        for pattern in patterns:
            if pattern.pattern_type == SeasonalPattern.WEEKLY:
                if pattern.strength > 0.3:
                    peak_days = ', '.join(pattern.peak_periods[:2])
                    recommendations.append(
                        f"Stock up before {peak_days} to meet higher weekly demand"
                    )
            
            elif pattern.pattern_type == SeasonalPattern.MONTHLY:
                if pattern.strength > 0.3:
                    recommendations.append(
                        f"Increase inventory at the {pattern.peak_periods[0]} of each month"
                    )
            
            elif pattern.pattern_type in [SeasonalPattern.YEARLY, SeasonalPattern.DISEASE_SEASON]:
                if pattern.strength > 0.3:
                    peak_months = ', '.join(pattern.peak_periods[:2])
                    recommendations.append(
                        f"Plan for increased demand in {peak_months}. "
                        f"Consider ordering 20-30% more stock 4-6 weeks before peak season."
                    )
                    
                    low_months = ', '.join(pattern.low_periods[:2])
                    recommendations.append(
                        f"Reduce orders during {low_months} to avoid overstock"
                    )
        
        # Add general recommendation based on overall variability
        cv = df['y'].std() / (df['y'].mean() + 0.001)
        if cv > 1.0:
            recommendations.append(
                "High demand variability detected. Consider maintaining higher safety stock."
            )
        
        return recommendations
    
    async def _save_patterns(
        self,
        drug_id: UUID,
        patterns: list[SeasonalityPatternSchema],
        analysis_days: int,
        df: pd.DataFrame
    ) -> None:
        """Save detected patterns to database."""
        try:
            for pattern in patterns:
                record = SeasonalityPatternModel(
                    drug_id=drug_id,
                    pattern_type=pattern.pattern_type.value,
                    strength=Decimal(str(pattern.strength)),
                    pattern_data={
                        'peak_periods': pattern.peak_periods,
                        'low_periods': pattern.low_periods,
                        'description': pattern.description
                    },
                    analysis_period_days=analysis_days,
                    analysis_start_date=df['ds'].min().date() if hasattr(df['ds'].min(), 'date') else df['ds'].min(),
                    analysis_end_date=df['ds'].max().date() if hasattr(df['ds'].max(), 'date') else df['ds'].max(),
                    description=pattern.description
                )
                
                self.session.add(record)
            
            self.session.commit()
            logger.info(f"Saved {len(patterns)} seasonality patterns for drug {drug_id}")
            
        except Exception as e:
            logger.error(f"Error saving seasonality patterns: {str(e)}")

