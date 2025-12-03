# Clinical Data Prediction Module

Predictive analytics module for the HUE healthcare platform. Provides medicine demand forecasting, expiry prediction, seasonal analysis, and anomaly detection.

## Features

### 1. Demand Forecasting

Forecast medicine demand using Facebook Prophet time-series models.

**Granularity Levels:**
- **Per Pharmacy**: Forecast total demand for a specific pharmacy
- **Per Drug**: Forecast platform-wide demand for a specific drug
- **Per Drug + Pharmacy**: Forecast demand for a specific drug at a specific pharmacy
- **Aggregate**: Forecast platform-wide demand for all drugs

**Forecast Horizons:**
- 7 days (weekly planning)
- 30 days (monthly planning)
- 90 days (quarterly planning)

### 2. Expiry/Waste Prediction

Analyze inventory for drugs at risk of expiring before being sold.

**Features:**
- Compare forecasted demand vs current inventory levels
- Calculate estimated waste quantities
- Risk level classification (low, medium, high, critical)
- Actionable recommendations (markdown pricing, transfers, etc.)

### 3. Seasonal Pattern Analysis

Detect demand patterns for better inventory planning.

**Pattern Types:**
- Weekly cycles (weekday vs weekend demand)
- Monthly patterns (beginning vs end of month)
- Yearly seasonality
- Disease season patterns (Ghana-specific: malaria season, respiratory season, etc.)

### 4. Anomaly Detection

Identify unusual demand patterns for early warning.

**Anomaly Types:**
- Demand spikes (potential outbreak signals)
- Demand drops (supply chain or data issues)
- Trend changes

**Methods:**
- Prophet uncertainty intervals
- Statistical Z-score detection

### 5. Smart Reorder Recommendations

Generate intelligent reorder suggestions based on forecasts.

**Factors Considered:**
- Predicted demand
- Current inventory levels
- Safety stock requirements
- Lead time for orders

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/clinical-prediction/forecast/demand` | POST | Generate demand forecast |
| `/clinical-prediction/forecast/pharmacy/{id}` | GET | Get forecasts for a pharmacy |
| `/clinical-prediction/forecast/drug/{id}` | GET | Get forecasts for a drug |
| `/clinical-prediction/analytics/expiry-risk` | POST | Get expiry risk report |
| `/clinical-prediction/analytics/seasonality/{drug_id}` | GET | Get seasonal patterns |
| `/clinical-prediction/analytics/anomalies` | GET | Get detected anomalies |
| `/clinical-prediction/forecast/reorder-recommendations` | POST | Get reorder suggestions |

## Database Models

### demand_forecasts
Stores forecast predictions for caching and accuracy tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| pharmacy_id | UUID | Pharmacy reference (nullable) |
| drug_id | UUID | Drug reference (nullable) |
| granularity | VARCHAR | Forecast granularity level |
| horizon_days | INT | Forecast horizon |
| forecast_data | JSONB | Array of forecast data points |
| total_predicted_demand | DECIMAL | Total predicted demand |
| confidence_score | DECIMAL | Model confidence (0-1) |

### demand_anomalies
Stores detected anomalies for alerting and tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| pharmacy_id | UUID | Affected pharmacy (nullable) |
| drug_id | UUID | Affected drug (nullable) |
| anomaly_type | VARCHAR | spike, drop, trend_change |
| anomaly_date | DATE | Date of anomaly |
| expected_demand | DECIMAL | Expected demand |
| actual_demand | DECIMAL | Actual observed demand |
| severity | VARCHAR | low, medium, high, critical |

### seasonality_patterns
Stores detected seasonal patterns for drugs.

## Usage Examples

### Generate Demand Forecast

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/clinical-prediction/forecast/demand",
    json={
        "granularity": "per_drug_pharmacy",
        "horizon_days": 30,
        "pharmacy_id": "uuid-here",
        "drug_id": "uuid-here",
        "include_confidence_intervals": True
    }
)
forecast = response.json()
```

### Get Expiry Risk Report

```python
response = httpx.post(
    "http://localhost:8000/api/v1/clinical-prediction/analytics/expiry-risk",
    json={
        "pharmacy_id": "uuid-here",
        "days_ahead": 90,
        "min_risk_level": "medium"
    }
)
risk_report = response.json()
```

### Get Reorder Recommendations

```python
response = httpx.post(
    "http://localhost:8000/api/v1/clinical-prediction/forecast/reorder-recommendations",
    json={
        "pharmacy_id": "uuid-here",
        "forecast_horizon": 30,
        "safety_stock_days": 7,
        "lead_time_days": 3
    }
)
recommendations = response.json()
```

## Dependencies

- `prophet>=1.1.5` - Time-series forecasting
- `pandas>=2.1.4` - Data manipulation
- `numpy>=1.26.4` - Numerical operations

## Architecture

```
clinical_data_prediction/
├── __init__.py
├── router.py                    # FastAPI endpoints
├── schemas.py                   # Pydantic models
├── demand_forecasting/
│   ├── __init__.py
│   ├── service.py               # Main orchestration
│   ├── prophet_forecaster.py    # Prophet model wrapper
│   ├── data_pipeline.py         # Data aggregation
│   └── models.py                # DB models
├── analytics/
│   ├── __init__.py
│   ├── expiry_predictor.py      # Expiry prediction
│   ├── seasonality_analyzer.py  # Pattern detection
│   └── anomaly_detector.py      # Anomaly detection
└── README.md
```

## Configuration

The module uses Prophet with the following default settings:
- Yearly seasonality: enabled
- Weekly seasonality: enabled
- Monthly seasonality: custom (30.5 day period)
- Confidence interval: 95%
- Seasonality mode: multiplicative

## Ghana-Specific Features

The seasonality analyzer includes Ghana-specific disease season detection:

| Season | Peak Months | Related Drugs |
|--------|-------------|---------------|
| Malaria | May-October | Artemether, Lumefantrine, Artesunate |
| Respiratory | Nov-February | Amoxicillin, Azithromycin, Cough medicines |
| Diarrhea | March-May | ORS, Zinc, Metronidazole |
| Skin Infections | June-September | Antifungals, Clotrimazole |

