from fastapi import APIRouter
from src.multi_disease_detector import router as multi_disease_detector_router
from src.drug_recommendation import router as drug_recommendation_router


# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include feature routers
api_router.include_router(multi_disease_detector_router)
api_router.include_router(drug_recommendation_router)


__all__ = ["api_router"]
