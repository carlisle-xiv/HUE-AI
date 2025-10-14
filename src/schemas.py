"""
General schemas module for common API schemas.
Feature-specific schemas are in their respective modules.
"""

from pydantic import BaseModel
from typing import Optional


class HealthCheck(BaseModel):
    """Schema for health check response"""

    status: str
    message: str
    version: Optional[str] = "1.0.0"


class ErrorResponse(BaseModel):
    """Schema for error responses"""

    error: str
    detail: Optional[str] = None


__all__ = ["HealthCheck", "ErrorResponse"]
