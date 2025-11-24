"""Uvicorn configuration optimized for SSE streaming"""

config = {
    "host": "0.0.0.0",
    "port": 8000,
    "timeout_keep_alive": 600,
    "limit_concurrency": None,
    "backlog": 2048,
    "log_level": "info",
    # For production, add:
    # "workers": 4,
    # "ssl_keyfile": "key.pem",
    # "ssl_certfile": "cert.pem",
}

