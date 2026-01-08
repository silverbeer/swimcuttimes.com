"""Health check endpoints."""

from fastapi import APIRouter

from swimcuttimes.api.dependencies import SettingsDep, SupabaseDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/health/ready")
def readiness_check(settings: SettingsDep, client: SupabaseDep) -> dict:
    """Readiness check - verifies database connectivity."""
    # Simple query to verify database connection
    client.table("events").select("id").limit(1).execute()

    return {
        "status": "ready",
        "environment": settings.environment.value,
        "database": "connected",
    }
