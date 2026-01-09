"""CLI authentication - login, logout, and token management.

Tokens are stored in ~/.swimcuttimes/credentials.json
"""

import contextlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel
from rich.console import Console

from swimcuttimes.config import get_settings

console = Console()

# Config directory
CONFIG_DIR = Path.home() / ".swimcuttimes"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


class StoredCredentials(BaseModel):
    """Credentials stored locally."""

    access_token: str
    refresh_token: str
    user_id: str
    email: str
    role: str
    display_name: str | None = None
    expires_at: datetime | None = None


def get_api_url() -> str:
    """Get API base URL from settings."""
    settings = get_settings()
    # For local dev, API runs on port 8000
    if settings.is_local:
        return "http://127.0.0.1:8000"
    # For cloud, would be the deployed API URL
    return settings.supabase_url.replace("supabase.co", "api.swimcuttimes.com")


def _ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_credentials(creds: StoredCredentials) -> None:
    """Save credentials to file."""
    _ensure_config_dir()
    CREDENTIALS_FILE.write_text(creds.model_dump_json(indent=2))
    # Secure permissions (owner read/write only)
    CREDENTIALS_FILE.chmod(0o600)


def load_credentials() -> StoredCredentials | None:
    """Load credentials from file."""
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_FILE.read_text())
        return StoredCredentials(**data)
    except (json.JSONDecodeError, ValueError):
        return None


def clear_credentials() -> None:
    """Remove stored credentials."""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return load_credentials() is not None


def get_auth_headers() -> dict[str, str]:
    """Get authorization headers for API requests."""
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Not logged in. Run: swimcuttimes auth login")
    return {"Authorization": f"Bearer {creds.access_token}"}


def api_request(
    method: str,
    path: str,
    *,
    json_data: dict[str, Any] | None = None,
    auth: bool = True,
) -> httpx.Response:
    """Make an API request.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., "/api/v1/auth/me")
        json_data: JSON body for POST/PUT/PATCH
        auth: Include auth headers (default: True)

    Returns:
        Response object

    Raises:
        RuntimeError: If not logged in and auth=True
        httpx.HTTPStatusError: If response is 4xx/5xx
    """
    url = f"{get_api_url()}{path}"
    headers = get_auth_headers() if auth else {}

    with httpx.Client() as client:
        response = client.request(method, url, json=json_data, headers=headers, timeout=30)

    return response


def login(email: str, password: str) -> StoredCredentials:
    """Login and store credentials.

    Args:
        email: User email
        password: User password

    Returns:
        Stored credentials

    Raises:
        RuntimeError: If login fails
    """
    response = api_request(
        "POST",
        "/api/v1/auth/login",
        json_data={"email": email, "password": password},
        auth=False,
    )

    if response.status_code == 401:
        raise RuntimeError("Invalid email or password")

    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.text}")

    data = response.json()

    creds = StoredCredentials(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        user_id=data["user"]["id"],
        email=email,
        role=data["user"]["role"],
        display_name=data["user"].get("display_name"),
    )

    save_credentials(creds)
    return creds


def logout() -> None:
    """Logout and clear credentials."""
    creds = load_credentials()
    if creds:
        with contextlib.suppress(Exception):
            api_request("POST", "/api/v1/auth/logout")

    clear_credentials()


def refresh_token() -> StoredCredentials | None:
    """Refresh the access token.

    Returns:
        Updated credentials or None if refresh failed
    """
    creds = load_credentials()
    if not creds:
        return None

    try:
        response = api_request(
            "POST",
            "/api/v1/auth/refresh",
            json_data={"refresh_token": creds.refresh_token},
            auth=False,
        )

        if response.status_code != 200:
            return None

        data = response.json()

        new_creds = StoredCredentials(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            user_id=data["user"]["id"],
            email=creds.email,
            role=data["user"]["role"],
            display_name=data["user"].get("display_name"),
        )

        save_credentials(new_creds)
        return new_creds

    except Exception:
        return None


def get_current_user() -> dict[str, Any] | None:
    """Get current user info from API.

    Returns:
        User data dict or None if not logged in
    """
    try:
        response = api_request("GET", "/api/v1/auth/me")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def require_auth() -> StoredCredentials:
    """Require authentication, raising error if not logged in.

    Returns:
        Current credentials

    Raises:
        RuntimeError: If not logged in
    """
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Not logged in. Run: swimcuttimes auth login")
    return creds


def require_admin() -> StoredCredentials:
    """Require admin role.

    Returns:
        Current credentials

    Raises:
        RuntimeError: If not logged in or not admin
    """
    creds = require_auth()
    if creds.role != "admin":
        raise RuntimeError("Admin access required")
    return creds
