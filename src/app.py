from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
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
    Application startup event.
    Preloads models and resources for optimal first-request performance.
    
    Environment Variables (from .env):
        PRELOAD_MODELS: "true" | "false" (REQUIRED) - Enable/disable model preloading
    """
    logger.info("Starting HUE-AI application...")
    logger.info("Multi Disease Detector using OpenRouter API (openai/gpt-oss-120b)")
    
    # Read from .env (no hardcoded default)
    preload_setting = os.getenv("PRELOAD_MODELS")
    
    if preload_setting is None:
        logger.warning("⚠ PRELOAD_MODELS not set in .env - defaulting to false for safety")
        should_preload = False
    else:
        should_preload = preload_setting.lower() == "true"
        logger.info(f"PRELOAD_MODELS={preload_setting} (from .env)")
    
    if should_preload:
        logger.info("Preloading MiniLM model for risk assessment...")
        from src.multi_disease_detector.risk_assessment import get_sentence_transformer
        model = get_sentence_transformer()
        
        if model is not None:
            logger.info("✓ MiniLM model preloaded successfully")
        else:
            logger.warning("⚠ MiniLM model failed to load - will use rule-based fallback")
    else:
        logger.info("Model preloading disabled (PRELOAD_MODELS=false or not set)")
        logger.info("Models will load on first use (adds ~7s to first request)")
    
    logger.info("✓ Application ready!")


# Include API router
app.include_router(api_router)


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    """Scalar API documentation"""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


@app.get("/", response_model=HealthCheck)
async def root():
    """Root endpoint - health check"""
    return HealthCheck(status="healthy", message="HUE-AI is running successfully")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    return HealthCheck(status="healthy", message="All systems operational")
