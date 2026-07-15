from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=200)
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }
