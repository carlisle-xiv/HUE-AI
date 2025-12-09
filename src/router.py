from fastapi import APIRouter
from src.multi_disease_detector import router as multi_disease_detector_router
from src.drug_recommendation import router as drug_recommendation_router
from src.drug_suggester.router import router as drug_suggester_router
# Direct import to avoid circular dependency through package __init__
from src.clinical_data_prediction.router import router as clinical_prediction_router
from src.STT_TTS.router import router as stt_tts_router


# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include feature routers
api_router.include_router(multi_disease_detector_router)
api_router.include_router(drug_recommendation_router)
api_router.include_router(drug_suggester_router)
api_router.include_router(clinical_prediction_router)
api_router.include_router(stt_tts_router)


__all__ = ["api_router"]
