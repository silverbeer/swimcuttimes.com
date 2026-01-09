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
.
├── backend/                  # Python backend
│   ├── src/swimcuttimes/     # Application source
│   │   ├── api/              # FastAPI application
│   │   │   ├── routes/       # API endpoints
│   │   │   └── dependencies/ # DI and middleware
│   │   ├── models/           # Pydantic models
│   │   └── cli/              # Typer CLI application
│   ├── tests/                # Pytest tests (mirrors src/)
│   ├── tools/                # Development tools
│   ├── data/                 # Data files (time standards)
│   └── pyproject.toml        # Python dependencies
├── frontend/                 # Frontend (Nuxt 3 - future)
├── supabase/                 # Database config & migrations
├── scripts/                  # Shared shell scripts
└── docs/                     # Project documentation
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

## Database Migrations

Migrations are stored in `supabase/migrations/` and committed to the repository. The migration workflow depends on whether you're creating new migrations or applying existing ones.

### Applying Migrations (Pull from Main)

When migration files have been added to the repo and you need to apply them to your local Supabase:

```bash
# 1. Pull latest changes from main
git pull origin main

# 2. Check migration status (see which migrations are pending)
./scripts/db.sh status

# 3. Apply pending migrations (non-destructive)
./scripts/db.sh migrate

# 4. Verify in Studio
./scripts/api.sh status  # Shows Studio URL
```

### Full Database Reset

If you need a clean slate (applies all migrations + seeds):

```bash
# WARNING: This destroys all local data (local environment only)
./scripts/db.sh reset
```

### Creating New Migrations

When you've made schema changes that need to be captured:

```bash
# Option 1: Generate migration from diff (if you made changes in Studio)
npx supabase db diff -f <migration_name>

# Option 2: Create empty migration file to write manually
npx supabase migration new <migration_name>

# Then edit the file in supabase/migrations/
```

### Migration File Naming

Files are named with timestamp prefix: `YYYYMMDDHHMMSS_description.sql`

Example: `20260108100000_auth_user_profiles.sql`

### Troubleshooting

```bash
# Check Supabase services status
npx supabase status

# View migration history
./scripts/db.sh status

# Repair migration history (if out of sync, local)
npx supabase migration repair --status applied <version> --local

# Repair migration history (if out of sync, remote)
npx supabase migration repair --status applied <version>
```
