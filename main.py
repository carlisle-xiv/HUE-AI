import uvicorn
from src.app import app

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=600,  # Keep connections alive for long streams
        limit_concurrency=None,  # No artificial limits
        backlog=2048,  # Handle bursts
        log_level="info"
    )
