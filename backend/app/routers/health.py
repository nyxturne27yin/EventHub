from fastapi import APIRouter

from app.services.health import get_health_status


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return get_health_status()
