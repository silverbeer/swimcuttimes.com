"""Authentication middleware and dependencies.

Usage:
    from swimcuttimes.api.auth import get_current_user, require_role

    @router.get("/protected")
    def protected_route(user: CurrentUser):
        return {"user_id": user.id}

    @router.get("/admin-only")
    def admin_route(user: CurrentUser = Depends(require_role(UserRole.ADMIN))):
        return {"admin": user.id}
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from swimcuttimes import get_logger
from swimcuttimes.api.dependencies import SupabaseDep
from swimcuttimes.models import UserProfile, UserRole

logger = get_logger(__name__)

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    client: SupabaseDep,
) -> UserProfile:
    """Verify JWT and return current user profile.

    Raises:
        HTTPException 401: Missing or invalid token
        HTTPException 403: User profile not found
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Verify token with Supabase Auth
        user_response = client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = UUID(user_response.user.id)

    except HTTPException:
        raise
    except Exception as e:
        logger.warning("auth_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Load user profile - set auth context for RLS
    client.postgrest.auth(token)
    result = (
        client.table("user_profiles")
        .select("*")
        .eq("id", str(user_id))
        .is_("deleted_at", "null")
        .execute()
    )

    if not result.data or len(result.data) == 0:
        logger.error("user_profile_missing", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not found",
        )

    profile_data = result.data[0]
    return UserProfile(
        id=UUID(profile_data["id"]),
        role=UserRole(profile_data["role"]),
        display_name=profile_data.get("display_name"),
        avatar_url=profile_data.get("avatar_url"),
        swimmer_id=UUID(profile_data["swimmer_id"]) if profile_data.get("swimmer_id") else None,
        created_at=profile_data.get("created_at"),
        updated_at=profile_data.get("updated_at"),
    )


# Type alias for dependency injection
CurrentUser = Annotated[UserProfile, Depends(get_current_user)]


def require_role(*allowed_roles: UserRole):
    """Dependency that requires user to have one of the allowed roles.

    Usage:
        @router.get("/coaches")
        def coaches_only(user: CurrentUser = Depends(require_role(UserRole.COACH, UserRole.ADMIN))):
            ...
    """

    async def check_role(user: CurrentUser) -> UserProfile:
        if user.role not in allowed_roles:
            logger.warning(
                "role_denied",
                user_id=str(user.id),
                user_role=user.role.value,
                required_roles=[r.value for r in allowed_roles],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(r.value for r in allowed_roles)}",
            )
        return user

    return check_role


def require_admin(user: CurrentUser) -> UserProfile:
    """Shorthand dependency for admin-only routes."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


AdminUser = Annotated[UserProfile, Depends(require_admin)]


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    client: SupabaseDep,
) -> UserProfile | None:
    """Get current user if authenticated, None otherwise.

    Useful for routes that behave differently for authenticated vs anonymous users.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, client)
    except HTTPException:
        return None


OptionalUser = Annotated[UserProfile | None, Depends(get_optional_user)]
