from sqlmodel import SQLModel
from src.database import engine
from src.models import *


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✓ Database tables created successfully!")


if __name__ == "__main__":
    create_tables()
