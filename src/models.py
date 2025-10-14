"""
General models module that imports all feature models.
This ensures all models are registered with SQLModel.
"""

from sqlmodel import SQLModel

# Import all feature models here
from src.health_assistant.models import HealthSession, HealthMessage

# Export for easy access
__all__ = [
    "SQLModel",
    "HealthSession",
    "HealthMessage",
]
