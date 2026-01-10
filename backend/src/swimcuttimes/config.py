"""Application configuration with environment validation.

Usage:
    from swimcuttimes.config import settings

    # Access configuration
    print(settings.supabase_url)
    print(settings.environment)

Environment files:
    - .env.local - Local development (local Supabase)
    - .env.dev   - Development (Supabase Cloud dev project)
    - .env.prod  - Production (Supabase Cloud prod project)

Switch environments:
    ./scripts/env.sh local
    ./scripts/env.sh dev
    ./scripts/env.sh prod
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> Path | None:
    """Find .env file, checking both current dir and project root."""
    # Check current directory first
    if Path(".env").exists():
        return Path(".env")
    # Check project root (parent of backend/)
    # config.py -> swimcuttimes -> src -> backend -> project_root
    project_root = Path(__file__).parent.parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        return env_file
    return None


class Environment(StrEnum):
    """Application environment."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    """Log output format."""

    CONSOLE = "console"
    JSON = "json"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Settings are loaded from .env file in the project root.
    Use ./scripts/env.sh to switch between environments.
    """

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: Environment = Environment.LOCAL

    # Supabase
    supabase_url: str = Field(description="Supabase project URL")
    supabase_key: SecretStr = Field(description="Supabase anon/public key")
    supabase_service_role_key: SecretStr | None = Field(
        default=None, description="Supabase service role key (bypasses RLS, for tests/admin)"
    )

    # Anthropic (optional - only needed for image parsing)
    anthropic_api_key: SecretStr | None = Field(
        default=None, description="Anthropic API key for image parsing"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: LogFormat = Field(default=LogFormat.CONSOLE, description="Log output format")

    @property
    def is_local(self) -> bool:
        """Check if running in local environment."""
        return self.environment == Environment.LOCAL

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Settings are loaded once and cached. To reload, clear the cache:
        get_settings.cache_clear()

    Returns:
        Application settings
    """
    return Settings()


# Convenience alias for direct import
settings = get_settings()
