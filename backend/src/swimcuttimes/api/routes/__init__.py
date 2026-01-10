"""API route modules."""

from swimcuttimes.api.routes.auth import router as auth_router
from swimcuttimes.api.routes.follows import router as follows_router
from swimcuttimes.api.routes.health import router as health_router
from swimcuttimes.api.routes.meets import router as meets_router
from swimcuttimes.api.routes.swim_times import router as swim_times_router
from swimcuttimes.api.routes.swim_times import swimmers_router as swimmer_times_router
from swimcuttimes.api.routes.swimmers import router as swimmers_router
from swimcuttimes.api.routes.teams import router as teams_router
from swimcuttimes.api.routes.time_standards import router as time_standards_router

__all__ = [
    "auth_router",
    "follows_router",
    "health_router",
    "meets_router",
    "swim_times_router",
    "swimmer_times_router",
    "swimmers_router",
    "teams_router",
    "time_standards_router",
]
