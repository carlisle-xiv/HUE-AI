"""
General router module that combines all feature routers.
"""

from fastapi import APIRouter


# Create main API router
api_router = APIRouter(prefix="/api/v1")


__all__ = ["api_router"]
