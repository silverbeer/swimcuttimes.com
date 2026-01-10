"""Fixtures for API tests."""

from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import Client, create_client

# Load environment variables before importing app
load_dotenv()

from swimcuttimes.api.app import create_app  # noqa: E402
from swimcuttimes.api.auth import get_current_user, require_admin, require_admin_or_coach  # noqa: E402
from swimcuttimes.api.dependencies import get_supabase  # noqa: E402
from swimcuttimes.config import get_settings  # noqa: E402
from swimcuttimes.models import UserProfile, UserRole  # noqa: E402


def _get_test_supabase_client() -> Client:
    """Get Supabase client with service_role key for tests (bypasses RLS)."""
    settings = get_settings()
    # Use service_role key if available, otherwise fall back to anon key
    key = settings.supabase_service_role_key or settings.supabase_key
    return create_client(settings.supabase_url, key.get_secret_value())


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
def coach_user() -> UserProfile:
    """Create a mock coach user."""
    return UserProfile(
        id=uuid4(),
        role=UserRole.COACH,
        display_name="Test Coach",
    )


@pytest.fixture
def client_as_admin(admin_user: UserProfile) -> TestClient:
    """Provide a test client authenticated as admin with service_role DB access."""
    app = create_app()

    # Use service_role client to bypass RLS for tests
    test_client = _get_test_supabase_client()

    def mock_get_supabase():
        return test_client

    async def mock_get_current_user():
        return admin_user

    def mock_require_admin():
        return admin_user

    app.dependency_overrides[get_supabase] = mock_get_supabase
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_admin] = mock_require_admin

    return TestClient(app)


@pytest.fixture
def client_as_user(regular_user: UserProfile) -> TestClient:
    """Provide a test client authenticated as regular user (no admin access)."""
    app = create_app()

    # Use service_role client to bypass RLS for tests
    test_client = _get_test_supabase_client()

    def mock_get_supabase():
        return test_client

    async def mock_get_current_user():
        return regular_user

    app.dependency_overrides[get_supabase] = mock_get_supabase
    app.dependency_overrides[get_current_user] = mock_get_current_user
    # Note: require_admin is NOT overridden, so admin routes will fail

    return TestClient(app)


@pytest.fixture
def client_unauthenticated() -> TestClient:
    """Provide a test client with no authentication."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def client_as_coach(coach_user: UserProfile) -> TestClient:
    """Provide a test client authenticated as coach (can manage swimmers)."""
    app = create_app()

    # Use service_role client to bypass RLS for tests
    test_client = _get_test_supabase_client()

    def mock_get_supabase():
        return test_client

    async def mock_get_current_user():
        return coach_user

    def mock_require_admin_or_coach():
        return coach_user

    app.dependency_overrides[get_supabase] = mock_get_supabase
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_admin_or_coach] = mock_require_admin_or_coach
    # Note: require_admin is NOT overridden, so admin-only routes will fail

    return TestClient(app)
