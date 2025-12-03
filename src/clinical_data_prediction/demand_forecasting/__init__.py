# Lazy imports to avoid circular dependencies during model loading
# Import these directly when needed:
# from src.clinical_data_prediction.demand_forecasting.service import DemandForecastingService
# from src.clinical_data_prediction.demand_forecasting.prophet_forecaster import ProphetForecaster
# from src.clinical_data_prediction.demand_forecasting.data_pipeline import DemandDataPipeline

__all__ = [
    "DemandForecastingService",
    "ProphetForecaster",
    "DemandDataPipeline",
]


def __getattr__(name):
    """Lazy loading of submodule components."""
    if name == "DemandForecastingService":
        from .service import DemandForecastingService
        return DemandForecastingService
    elif name == "ProphetForecaster":
        from .prophet_forecaster import ProphetForecaster
        return ProphetForecaster
    elif name == "DemandDataPipeline":
        from .data_pipeline import DemandDataPipeline
        return DemandDataPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

