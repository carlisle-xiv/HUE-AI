"""
General router module that combines all feature routers.
"""

from fastapi import APIRouter

# Import feature routers
from src.health_assistant.router import router as health_assistant_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all feature routers
api_router.include_router(health_assistant_router)

__all__ = ["api_router"]
