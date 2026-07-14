"""Shared FastAPI dependencies for LegalClear API routers."""

from fastapi import Header, HTTPException

from src.core.config import settings


def require_api_key(x_api_key: str = Header(default="")):
    """FastAPI dependency: require valid API key.

    Use as: @router.get("/endpoint", dependencies=[Depends(require_api_key)])
    """
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
