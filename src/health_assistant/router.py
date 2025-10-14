from fastapi import APIRouter

# Placeholder for health assistant routes
# Will be implemented after database setup
router = APIRouter(prefix="/health-assistant", tags=["Health Assistant"])


@router.get("/")
async def health_assistant_root():
    """Health assistant root endpoint"""
    return {"message": "Health Assistant API - Ready to help with your health queries"}
