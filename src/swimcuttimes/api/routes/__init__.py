"""API route modules."""

from swimcuttimes.api.routes.auth import router as auth_router
from swimcuttimes.api.routes.follows import router as follows_router
from swimcuttimes.api.routes.health import router as health_router
from swimcuttimes.api.routes.time_standards import router as time_standards_router

__all__ = ["auth_router", "follows_router", "health_router", "time_standards_router"]
