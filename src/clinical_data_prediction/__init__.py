# Lazy import to avoid circular dependency with models
def get_router():
    from .router import router
    return router

__all__ = ["get_router"]

