# Architecture

## Tech Stack

- **Backend**: FastAPI + Pydantic (Python 3.11+)
- **Database**: Supabase (PostgreSQL) - local development, cloud later
- **CLI**: Typer + Rich
- **Package Management**: uv + pyproject.toml
- **Linting**: ruff (via uv tools)
- **Testing**: pytest + pytest-cov
- **CI/CD**: GitHub Actions
- **Frontend** (future): Nuxt 3 + Tailwind CSS

## Project Structure

```
src/
├── api/              # FastAPI application
│   ├── routes/       # API endpoints
│   └── dependencies/ # DI and middleware
├── models/           # Pydantic models for swim data
├── cli/              # Typer CLI application
└── parser/           # Image parsing tool (defines data model)
scripts/              # DB init, migrate, seed scripts
tests/                # Pytest tests (mirrors src/ structure)
supabase/             # Supabase local config & migrations
docs/                 # Project documentation
```

## Design Principles

### API-First
The CLI consumes the FastAPI backend. This ensures:
- Consistent behavior between CLI and future web frontend
- API is always the source of truth
- Easy to add new clients (web, mobile) later

### Image Parser First
The image parser tool is built first because it:
- Defines the core data models for swim meet time standards
- Establishes Pydantic models shared across the entire application
- Drives the database schema design

### Service Layer Pattern
Business logic lives in service classes, not route handlers:
- Route handlers only handle HTTP concerns (request/response)
- Services contain all business logic
- Enables unit testing without HTTP overhead

### Dependency Injection
External services (database, external APIs) are injected:
- Easy to mock in tests
- Swap implementations without changing business logic
- FastAPI's `Depends()` for injection

### Shared Pydantic Models
Single source of truth for data structures:
- Used in API request/response validation
- Used in database operations
- Used in CLI input/output
- Used in parser output
