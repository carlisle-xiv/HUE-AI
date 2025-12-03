
# Lazy imports to avoid circular dependencies during model loading
# Import these directly when needed:
# from src.clinical_data_prediction.analytics.expiry_predictor import ExpiryPredictor
# from src.clinical_data_prediction.analytics.seasonality_analyzer import SeasonalityAnalyzer
# from src.clinical_data_prediction.analytics.anomaly_detector import AnomalyDetector

__all__ = [
    "ExpiryPredictor",
    "SeasonalityAnalyzer",
    "AnomalyDetector",
]


def __getattr__(name):
    """Lazy loading of submodule components."""
    if name == "ExpiryPredictor":
        from .expiry_predictor import ExpiryPredictor
        return ExpiryPredictor
    elif name == "SeasonalityAnalyzer":
        from .seasonality_analyzer import SeasonalityAnalyzer
        return SeasonalityAnalyzer
    elif name == "AnomalyDetector":
        from .anomaly_detector import AnomalyDetector
        return AnomalyDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

