"""FastAPI application factory.

Usage:
    # Development
    uv run fastapi dev src/swimcuttimes/api/app.py

    # Production
    uv run fastapi run src/swimcuttimes/api/app.py
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from swimcuttimes import configure_logging, get_logger
from swimcuttimes.api.routes import (
    auth_router,
    follows_router,
    health_router,
    swimmers_router,
    teams_router,
    time_standards_router,
)
from swimcuttimes.config import get_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    settings = get_settings()
    configure_logging()
    logger.info(
        "app_starting",
        environment=settings.environment.value,
        supabase_url=settings.supabase_url,
    )
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Swim Cut Times API",
        description="Track swim times and qualification standards",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # Register routes
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(follows_router, prefix="/api/v1")
    app.include_router(swimmers_router, prefix="/api/v1")
    app.include_router(teams_router, prefix="/api/v1")
    app.include_router(time_standards_router, prefix="/api/v1")

    return app


# Application instance for uvicorn
app = create_app()
