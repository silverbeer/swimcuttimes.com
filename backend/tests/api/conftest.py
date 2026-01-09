"""Fixtures for API tests."""

from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Load environment variables before importing app
load_dotenv()

from swimcuttimes.api.app import create_app  # noqa: E402
from swimcuttimes.api.auth import get_current_user, require_admin  # noqa: E402
from swimcuttimes.models import UserProfile, UserRole  # noqa: E402


@pytest.fixture
def admin_user() -> UserProfile:
    """Create a mock admin user."""
    return UserProfile(
        id=uuid4(),
        role=UserRole.ADMIN,
        display_name="Test Admin",
    )


@pytest.fixture
def regular_user() -> UserProfile:
    """Create a mock regular user."""
    return UserProfile(
        id=uuid4(),
        role=UserRole.SWIMMER,
        display_name="Test User",
    )


@pytest.fixture
def client_as_admin(admin_user: UserProfile) -> TestClient:
    """Provide a test client authenticated as admin."""
    app = create_app()

    async def mock_get_current_user():
        return admin_user

    def mock_require_admin():
        return admin_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_admin] = mock_require_admin

    return TestClient(app)


@pytest.fixture
def client_as_user(regular_user: UserProfile) -> TestClient:
    """Provide a test client authenticated as regular user (no admin access)."""
    app = create_app()

    async def mock_get_current_user():
        return regular_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    # Note: require_admin is NOT overridden, so admin routes will fail

    return TestClient(app)


@pytest.fixture
def client_unauthenticated() -> TestClient:
    """Provide a test client with no authentication."""
    app = create_app()
    return TestClient(app)
