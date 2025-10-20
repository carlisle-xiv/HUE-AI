"""
General models module that imports all models.
This ensures all models are registered with SQLModel.
"""

from sqlmodel import SQLModel

# Import all models from the models package
from src.models import *  # noqa: F401, F403

# Export for easy access
__all__ = [
    "SQLModel",
]
