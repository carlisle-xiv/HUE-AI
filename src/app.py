"""
Main FastAPI application setup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

from src.router import api_router
from src.schemas import HealthCheck

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title=os.getenv("APP_NAME", "HUE-AI"),
    description="AI-powered health and wellness assistant platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """
    Load AI models on application startup.
    This ensures models are ready before handling requests.
    """
    logger.info("Starting HUE-AI application...")
    logger.info("Loading AI models (this may take a few minutes)...")

    try:
        # Import and initialize model service (loads models)
        from src.health_assistant.model_service import model_service

        # Check model status
        status = model_service.health_check()
        logger.info(f"Model Service Status: {status}")

        if status["biomistral_ready"] and status["llava_ready"]:
            logger.info("✓ All AI models loaded successfully!")
        else:
            logger.warning("⚠ Some models failed to load. Service may be degraded.")

    except Exception as e:
        logger.error(f"✗ Failed to load AI models: {str(e)}")
        logger.warning(
            "Application will start but health assistant features may not work."
        )


# Include API router
app.include_router(api_router)


@app.get("/", response_model=HealthCheck)
async def root():
    """Root endpoint - health check"""
    return HealthCheck(status="healthy", message="HUE-AI is running successfully")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(status="healthy", message="All systems operational")
