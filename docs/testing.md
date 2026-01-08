# Testing

## Philosophy

**High code coverage is a priority.** All complex/key logic must be isolated into pure functions or service classes to enable thorough unit testing.

## Commands

```bash
uv run pytest                              # Run all tests
uv run pytest -k "test_name"               # Run specific test
uv run pytest tests/parser/                # Run tests in directory
uv run pytest --cov=src                    # Run with coverage
uv run pytest --cov=src --cov-report=html  # Coverage HTML report
uv run pytest -x                           # Stop on first failure
uv run pytest -v                           # Verbose output
```

## Test Structure

Tests mirror the source structure:
```
tests/
├── api/          # API route tests
├── models/       # Pydantic model tests
├── parser/       # Image parser tests
├── cli/          # CLI command tests
├── conftest.py   # Shared fixtures
└── factories/    # Test data factories
```

## Test Types

### Unit Tests
For pure logic with no external dependencies:
- Parsing functions
- Validation logic
- Time calculations and conversions
- Business rules

Example locations:
- `tests/parser/test_time_parser.py`
- `tests/models/test_validators.py`

### Integration Tests
For API endpoints using FastAPI TestClient:
- Route behavior
- Request/response validation
- Error handling

Example:
```python
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_swimmer():
    response = client.get("/swimmers/1")
    assert response.status_code == 200
```

### Database Tests
For database operations with test fixtures:
- Use isolated test database
- Fixtures create/teardown test data
- Test actual SQL/ORM behavior

## Fixtures

Common fixtures in `conftest.py`:
- `db_session` - Isolated database session
- `test_swimmer` - Sample swimmer
- `test_team` - Sample team
- `test_time_standards` - Sample time standards

## Mocking

Use dependency injection to mock external services:
```python
from unittest.mock import Mock

def test_with_mock_db(mocker):
    mock_db = Mock()
    mock_db.get_swimmer.return_value = sample_swimmer
    # Test with mock
```

## Coverage Goals

- Aim for >80% coverage overall
- 100% coverage on business logic (services, parsers)
- Integration tests cover happy path + error cases
