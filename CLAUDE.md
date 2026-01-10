# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Stack**: FastAPI + Pydantic, Supabase (PostgreSQL), Typer + Rich CLI, uv + pyproject.toml

```bash
# Backend development (run from backend/)
cd backend
uv sync                    # Install dependencies
uv run python -m cli       # Run CLI
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run pytest              # Run tests
uv run pytest --cov=src    # Run with coverage

# API server (run from project root)
./scripts/api.sh start     # Start API server (background)
./scripts/api.sh stop      # Stop API server
./scripts/api.sh status    # Check API server status
./scripts/api.sh logs      # Tail API server logs

# Environment (run from project root)
./scripts/env.sh local     # Switch to local Supabase
./scripts/env.sh dev       # Switch to dev cloud
./scripts/env.sh prod      # Switch to prod cloud
./scripts/env.sh status    # Show current environment

# Database (run from project root, environment-aware)
./scripts/db.sh status    # Show migration status
./scripts/db.sh migrate   # Apply pending migrations
./scripts/db.sh reset     # Reset DB (local only, migrations + seed)
./scripts/db.sh start     # Start local Supabase
./scripts/db.sh stop      # Stop local Supabase
```

## Project Structure

```
.
├── backend/              # Python backend (FastAPI + CLI)
│   ├── src/swimcuttimes/ # Application source code
│   ├── tests/            # Pytest tests
│   ├── tools/            # Development tools
│   ├── data/             # Data files (time standards)
│   └── pyproject.toml    # Python dependencies
├── frontend/             # Frontend (Nuxt 3 - future)
├── supabase/             # Database config & migrations
├── scripts/              # Shared shell scripts
└── docs/                 # Documentation
```

## Key Principles

- **API-first**: CLI consumes the FastAPI backend
- **Service layer**: Business logic in services, not route handlers (enables testing)
- **Dependency injection**: External services injected for easy mocking
- **High test coverage**: Complex logic isolated into testable pure functions

## Supabase Row Level Security (RLS)

**CRITICAL**: All tables in the `public` schema MUST have Row Level Security enabled.

When creating new tables in migrations:

1. **Always enable RLS** immediately after creating the table:
   ```sql
   CREATE TABLE my_table (...);
   ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;
   ```

2. **Always add RLS policies** for the table. Common patterns:
   ```sql
   -- Public read access (for public data like swim times, meets, teams)
   CREATE POLICY "Table is publicly readable"
       ON my_table FOR SELECT
       USING (true);

   -- Admin/coach write access
   CREATE POLICY "Admins and coaches can create"
       ON my_table FOR INSERT
       WITH CHECK (is_admin() OR is_coach());

   -- User-owned data
   CREATE POLICY "Users can update own records"
       ON my_table FOR UPDATE
       USING (user_id = auth.uid());
   ```

3. **Use existing helper functions** for role checks:
   - `is_admin()` - Returns true if current user has admin role
   - `is_coach()` - Returns true if current user has coach role
   - `get_user_role(user_id)` - Returns the role for a specific user

4. **Policy naming convention**: Use descriptive names like:
   - `"Teams are publicly readable"`
   - `"Admins and coaches can create teams"`
   - `"Swimmers can update own record"`

**Why this matters**: Tables without RLS are accessible to anyone with the Supabase anon key, which is exposed in the frontend. Supabase will show security warnings for tables without RLS.

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

## Testing Requirements

**CRITICAL**: When writing tests, you MUST:

1. **Execute the tests** - Actually run `uv run pytest` on any tests you write
2. **Verify they pass** - If tests fail, fix them before reporting completion
3. **Fix failures, don't skip** - If a test fails due to code issues, fix the code or test
4. **Re-run after fixes** - Always re-run tests after making changes to confirm they pass

Never report "tests complete" without having successfully executed them. This includes checking for import errors, missing dependencies, and actual test failures.

```bash
# Run specific test file
uv run pytest tests/api/test_swimmers.py -v

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

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
