# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Stack**: FastAPI + Pydantic, Supabase (PostgreSQL), Typer + Rich CLI, uv + pyproject.toml

```bash
# Development
uv sync                    # Install dependencies
./scripts/api.sh start     # Start API server (background)
./scripts/api.sh stop      # Stop API server
./scripts/api.sh status    # Check API server status
./scripts/api.sh logs      # Tail API server logs
uv run python -m cli       # Run CLI

# Quality
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run pytest              # Run tests
uv run pytest --cov=src    # Run with coverage

# Environment
./scripts/env.sh local     # Switch to local Supabase
./scripts/env.sh dev       # Switch to dev cloud
./scripts/env.sh prod      # Switch to prod cloud
./scripts/env.sh status    # Show current environment

# Database
./scripts/db-init.sh       # Initialize local Supabase
./scripts/db-migrate.sh    # Run migrations
./scripts/db-seed.sh       # Seed data
```

## Key Principles

- **API-first**: CLI consumes the FastAPI backend
- **Service layer**: Business logic in services, not route handlers (enables testing)
- **Dependency injection**: External services injected for easy mocking
- **High test coverage**: Complex logic isolated into testable pure functions

## Environment Configuration

Three environments are supported: **local**, **dev**, and **prod**.

**Setup:**
1. Copy `.env.local.example` to `.env.local` and fill in local Supabase credentials
2. Copy `.env.dev.example` to `.env.dev` with dev cloud credentials
3. Copy `.env.prod.example` to `.env.prod` with prod cloud credentials

**Switching environments:**
```bash
./scripts/env.sh local   # Local Supabase (supabase start)
./scripts/env.sh dev     # Dev cloud database
./scripts/env.sh prod    # Prod cloud database (prompts for confirmation)
./scripts/env.sh status  # Show current active environment
```

**Configuration in code:**
```python
from swimcuttimes.config import settings

# Access settings
settings.supabase_url       # Database URL
settings.environment        # "local", "development", "production"
settings.is_local           # True if local environment
settings.is_production      # True if production environment
```

**Files:**
- `.env` - Active environment (not committed, created by scripts)
- `.env.local` - Local secrets (not committed)
- `.env.dev` - Dev secrets (not committed)
- `.env.prod` - Prod secrets (not committed)
- `.env.*.example` - Templates (committed)

## Handling Warnings

When running tests or code that produces warnings (deprecation, etc.):

1. **Always communicate warnings** - Report them to the user, don't silently ignore
2. **Review if fixable** - Check if the warning is in our code (fix it) or third-party (can't fix)
3. **Never suppress without permission** - Do not add pytest filterwarnings or other suppression without explicit user approval

## Logging

Use `structlog` for all application logging. Console format for dev, JSON for prod.

```python
from swimcuttimes import configure_logging, get_logger, bind_context

# Call once at app startup
configure_logging()

# Get logger in any module
logger = get_logger(__name__)

# Log with structured context
logger.info("user_action", user_id="123", action="login")
logger.warning("slow_query", duration_ms=1500)
logger.exception("unhandled_error")  # Includes stack trace

# Bind context for request lifecycle
bind_context(request_id="abc123", user_id="456")
```

**Environment variables:**
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `LOG_FORMAT`: json, console (default: console for dev, json for prod)
- `ENVIRONMENT`: development, production, test (default: development)

**Guidelines:**
- Use snake_case event names: `user_logged_in`, `request_completed`
- Include relevant context as kwargs, not in the message string
- Use `logger.exception()` in except blocks to capture stack traces
- Bind `request_id` at start of each request for traceability

## Documentation

See `docs/` for detailed documentation:
- [Architecture](docs/architecture.md) - Tech stack, project structure, design principles
- [Domain Model](docs/domain-model.md) - Entities, relationships, multi-user support
- [Testing](docs/testing.md) - Test commands, patterns, coverage goals
