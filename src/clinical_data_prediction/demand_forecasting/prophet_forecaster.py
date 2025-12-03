import logging
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from decimal import Decimal

import pandas as pd
import numpy as np

# Prophet import with error handling
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not installed. Using fallback forecasting.")

# Configure logging - suppress Prophet's verbose output
logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class ProphetForecaster:
    """
    Prophet-based forecaster with multi-horizon support.
    """
    
    MODEL_VERSION = "prophet-1.1"
    
    def __init__(
        self,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
        seasonality_mode: str = 'multiplicative',
        interval_width: float = 0.95
    ):
        """
        Initialize the forecaster.
        
        Args:
            yearly_seasonality: Include yearly patterns
            weekly_seasonality: Include weekly patterns (weekday vs weekend)
            daily_seasonality: Include daily patterns (usually not needed)
            seasonality_mode: 'additive' or 'multiplicative'
            interval_width: Confidence interval width (0.80, 0.90, 0.95)
        """
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.seasonality_mode = seasonality_mode
        self.interval_width = interval_width
        self.model: Optional[Prophet] = None
        self.training_data: Optional[pd.DataFrame] = None
    
    def fit(self, df: pd.DataFrame) -> 'ProphetForecaster':
        """
        Fit the Prophet model to historical data.
        
        Args:
            df: DataFrame with columns 'ds' (date) and 'y' (value)
            
        Returns:
            self for chaining
        """
        if not PROPHET_AVAILABLE:
            logger.warning("Prophet not available, using fallback")
            self.training_data = df.copy()
            return self
        
        if df.empty or len(df) < 7:
            logger.warning("Insufficient data for forecasting (< 7 data points)")
            self.training_data = df.copy()
            return self
        
        # Ensure proper column types
        df = df.copy()
        df['ds'] = pd.to_datetime(df['ds'])
        df['y'] = df['y'].astype(float)
        
        # Remove any negative values (demand can't be negative)
        df.loc[df['y'] < 0, 'y'] = 0
        
        logger.info(f"Training Prophet model with {len(df)} data points")
        
        try:
            # Initialize Prophet model
            self.model = Prophet(
                yearly_seasonality=self.yearly_seasonality,
                weekly_seasonality=self.weekly_seasonality,
                daily_seasonality=self.daily_seasonality,
                seasonality_mode=self.seasonality_mode,
                interval_width=self.interval_width,
                uncertainty_samples=1000  # For confidence intervals
            )
            
            # Add custom seasonalities for healthcare domain
            # Monthly seasonality (payday effects, beginning/end of month patterns)
            self.model.add_seasonality(
                name='monthly',
                period=30.5,
                fourier_order=5
            )
            
            # Fit the model (suppressing output)
            self.model.fit(df)
            self.training_data = df.copy()
            
            logger.info("Prophet model trained successfully")
            
        except Exception as e:
            logger.error(f"Error training Prophet model: {str(e)}")
            self.training_data = df.copy()
            self.model = None
        
        return self
    
    def predict(
        self,
        horizon_days: int,
        include_history: bool = False
    ) -> pd.DataFrame:
        """
        Generate forecast for specified horizon.
        
        Args:
            horizon_days: Number of days to forecast ahead
            include_history: Include historical fitted values
            
        Returns:
            DataFrame with forecast columns: ds, yhat, yhat_lower, yhat_upper
        """
        if not PROPHET_AVAILABLE or self.model is None:
            return self._fallback_predict(horizon_days)
        
        try:
            # Create future DataFrame
            future = self.model.make_future_dataframe(
                periods=horizon_days,
                include_history=include_history
            )
            
            # Generate forecast
            forecast = self.model.predict(future)
            
            # Select relevant columns and filter to future only
            result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            
            if not include_history:
                # Keep only future predictions
                last_training_date = self.training_data['ds'].max()
                result = result[result['ds'] > last_training_date]
            
            # Ensure non-negative predictions (demand can't be negative)
            result['yhat'] = result['yhat'].clip(lower=0)
            result['yhat_lower'] = result['yhat_lower'].clip(lower=0)
            result['yhat_upper'] = result['yhat_upper'].clip(lower=0)
            
            logger.info(f"Generated {len(result)} forecast points for {horizon_days} days")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating forecast: {str(e)}")
            return self._fallback_predict(horizon_days)
    
    def _fallback_predict(self, horizon_days: int) -> pd.DataFrame:
        """
        Fallback prediction using simple moving average when Prophet fails.
        """
        logger.info("Using fallback moving average prediction")
        
        if self.training_data is None or self.training_data.empty:
            # Return zeros if no training data
            future_dates = pd.date_range(
                start=datetime.utcnow().date(),
                periods=horizon_days,
                freq='D'
            )
            return pd.DataFrame({
                'ds': future_dates,
                'yhat': [0.0] * horizon_days,
                'yhat_lower': [0.0] * horizon_days,
                'yhat_upper': [0.0] * horizon_days
            })
        
        # Calculate moving average from last 30 days
        recent_data = self.training_data.tail(30)
        avg_demand = recent_data['y'].mean()
        std_demand = recent_data['y'].std()
        
        if pd.isna(avg_demand):
            avg_demand = 0
        if pd.isna(std_demand):
            std_demand = 0
        
        # Generate future dates
        last_date = self.training_data['ds'].max()
        if isinstance(last_date, str):
            last_date = pd.to_datetime(last_date)
        
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=horizon_days,
            freq='D'
        )
        
        # Simple prediction with confidence intervals
        return pd.DataFrame({
            'ds': future_dates,
            'yhat': [max(0, avg_demand)] * horizon_days,
            'yhat_lower': [max(0, avg_demand - 1.96 * std_demand)] * horizon_days,
            'yhat_upper': [avg_demand + 1.96 * std_demand] * horizon_days
        })
    
    def get_trend_direction(self) -> str:
        """
        Determine the overall trend direction from the model.
        
        Returns:
            'increasing', 'decreasing', or 'stable'
        """
        if self.training_data is None or len(self.training_data) < 14:
            return 'stable'
        
        try:
            # Compare recent period to earlier period
            df = self.training_data.copy()
            recent = df.tail(14)['y'].mean()
            earlier = df.head(14)['y'].mean()
            
            if pd.isna(recent) or pd.isna(earlier):
                return 'stable'
            
            if earlier == 0:
                return 'increasing' if recent > 0 else 'stable'
            
            change_pct = (recent - earlier) / earlier * 100
            
            if change_pct > 10:
                return 'increasing'
            elif change_pct < -10:
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception:
            return 'stable'
    
    def get_confidence_score(self) -> float:
        """
        Calculate a confidence score for the forecast.
        Based on data quality and model fit.
        
        Returns:
            Confidence score between 0 and 1
        """
        if self.training_data is None or self.training_data.empty:
            return 0.0
        
        score = 0.5  # Base score
        
        # More data = higher confidence
        data_points = len(self.training_data)
        if data_points >= 365:
            score += 0.2
        elif data_points >= 180:
            score += 0.15
        elif data_points >= 90:
            score += 0.1
        elif data_points >= 30:
            score += 0.05
        
        # More non-zero days = higher confidence
        non_zero_ratio = (self.training_data['y'] > 0).sum() / len(self.training_data)
        score += non_zero_ratio * 0.2
        
        # Lower variance = higher confidence (more predictable)
        cv = self.training_data['y'].std() / (self.training_data['y'].mean() + 0.001)
        if cv < 0.5:
            score += 0.1
        elif cv < 1.0:
            score += 0.05
        
        return min(score, 1.0)
    
    def get_seasonality_components(self) -> Optional[dict]:
        """
        Extract seasonality components from the fitted model.
        
        Returns:
            Dictionary with seasonality information or None
        """
        if not PROPHET_AVAILABLE or self.model is None:
            return None
        
        try:
            # Get the seasonality DataFrames
            components = {}
            
            if self.weekly_seasonality:
                weekly = self.model.plot_components_plotly(
                    self.model.predict(self.model.make_future_dataframe(periods=0))
                )
                # Extract weekly pattern info
                components['weekly'] = {
                    'enabled': True,
                    'peak_day': self._get_peak_weekday()
                }
            
            if self.yearly_seasonality:
                components['yearly'] = {
                    'enabled': True,
                    'has_pattern': True
                }
            
            return components
            
        except Exception as e:
            logger.warning(f"Could not extract seasonality: {str(e)}")
            return None
    
    def _get_peak_weekday(self) -> Optional[str]:
        """
        Determine which weekday has highest average demand.
        """
        if self.training_data is None:
            return None
        
        try:
            df = self.training_data.copy()
            df['ds'] = pd.to_datetime(df['ds'])
            df['weekday'] = df['ds'].dt.day_name()
            
            avg_by_day = df.groupby('weekday')['y'].mean()
            peak_day = avg_by_day.idxmax()
            
            return peak_day
            
        except Exception:
            return None
    
    def detect_anomalies(
        self,
        threshold_sigma: float = 2.0
    ) -> list[dict]:
        """
        Detect anomalies in the training data using the fitted model.
        
        Args:
            threshold_sigma: Number of standard deviations for anomaly threshold
            
        Returns:
            List of detected anomalies
        """
        if not PROPHET_AVAILABLE or self.model is None or self.training_data is None:
            return []
        
        try:
            # Get fitted values with uncertainty
            fitted = self.model.predict(self.training_data)
            
            # Merge with actuals
            comparison = self.training_data.merge(
                fitted[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
                on='ds'
            )
            
            # Calculate residuals
            comparison['residual'] = comparison['y'] - comparison['yhat']
            
            # Identify anomalies (outside confidence interval)
            anomalies = []
            
            for _, row in comparison.iterrows():
                if row['y'] > row['yhat_upper']:
                    deviation_pct = (row['y'] - row['yhat']) / (row['yhat'] + 0.001) * 100
                    anomalies.append({
                        'date': row['ds'],
                        'type': 'spike',
                        'expected': row['yhat'],
                        'actual': row['y'],
                        'deviation_percentage': deviation_pct
                    })
                elif row['y'] < row['yhat_lower'] and row['yhat'] > 0:
                    deviation_pct = (row['y'] - row['yhat']) / (row['yhat'] + 0.001) * 100
                    anomalies.append({
                        'date': row['ds'],
                        'type': 'drop',
                        'expected': row['yhat'],
                        'actual': row['y'],
                        'deviation_percentage': deviation_pct
                    })
            
            return anomalies
            
        except Exception as e:
            logger.warning(f"Error detecting anomalies: {str(e)}")
            return []
    
    @staticmethod
    def forecast_to_datapoints(
        forecast: pd.DataFrame,
        include_bounds: bool = True
    ) -> list[dict]:
        """
        Convert forecast DataFrame to list of data points.
        
        Args:
            forecast: DataFrame with ds, yhat, yhat_lower, yhat_upper
            include_bounds: Include confidence interval bounds
            
        Returns:
            List of forecast data point dictionaries
        """
        result = []
        
        for _, row in forecast.iterrows():
            point = {
                'forecast_date': row['ds'].date() if hasattr(row['ds'], 'date') else row['ds'],
                'predicted_quantity': round(float(row['yhat']), 2)
            }
            
            if include_bounds:
                point['lower_bound'] = round(float(row['yhat_lower']), 2)
                point['upper_bound'] = round(float(row['yhat_upper']), 2)
            
            result.append(point)
        
        return result
    
    @staticmethod
    def calculate_total_demand(forecast: pd.DataFrame) -> Tuple[float, float]:
        """
        Calculate total and average daily demand from forecast.
        
        Args:
            forecast: DataFrame with yhat column
            
        Returns:
            Tuple of (total_demand, average_daily_demand)
        """
        total = float(forecast['yhat'].sum())
        average = float(forecast['yhat'].mean())
        
        return total, average

