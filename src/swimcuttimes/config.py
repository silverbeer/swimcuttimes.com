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
    ./scripts/use-local.sh
    ./scripts/use-dev.sh
    ./scripts/use-prod.sh
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    Use ./scripts/use-*.sh to switch between environments.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: Environment = Environment.LOCAL

    # Supabase
    supabase_url: str = Field(description="Supabase project URL")
    supabase_key: SecretStr = Field(description="Supabase anon/public key")

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
