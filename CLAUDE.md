# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Stack**: FastAPI + Pydantic, Supabase (PostgreSQL), Typer + Rich CLI, uv + pyproject.toml

```bash
# Development
uv sync                    # Install dependencies
uv run fastapi dev         # Run API dev server
uv run python -m cli       # Run CLI

# Quality
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run pytest              # Run tests
uv run pytest --cov=src    # Run with coverage

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
