"""Authentication and invitation endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from supabase_auth.types import (
    SignInWithEmailAndPasswordCredentials,
    SignUpWithEmailAndPasswordCredentials,
)
from pydantic import BaseModel, EmailStr

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminUser, CurrentUser
from swimcuttimes.api.dependencies import SupabaseDep
from swimcuttimes.models import (
    Invitation,
    InvitationCreate,
    InvitationStatus,
    UserProfile,
    UserRole,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class SignupRequest(BaseModel):
    """Signup with invitation token."""

    email: EmailStr
    password: str
    token: str  # Invitation token
    display_name: str | None = None


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response with tokens."""

    access_token: str
    refresh_token: str
    user: UserProfile


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


# =============================================================================
# AUTH ENDPOINTS
# =============================================================================


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, client: SupabaseDep) -> AuthResponse:
    """Register with an invitation token."""
    # Find and validate invitation
    result = (
        client.table("invitations")
        .select("*")
        .eq("token", request.token)
        .eq("status", "pending")
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token",
        )

    invitation = result.data

    # Check expiry
    if invitation["expires_at"]:
        expires_at = datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(expires_at.tzinfo):
            # Mark as expired
            client.table("invitations").update({"status": "expired"}).eq(
                "id", invitation["id"]
            ).execute()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired",
            )

    # Verify email matches invitation
    if invitation["email"].lower() != request.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email does not match invitation",
        )

    # Create user in Supabase Auth
    try:
        credentials: SignUpWithEmailAndPasswordCredentials = {
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "display_name": request.display_name or request.email.split("@")[0],
                }
            },
        }
        auth_response = client.auth.sign_up(credentials)
    except Exception as e:
        logger.error("signup_failed", error=str(e), email=request.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account",
        ) from e

    if not auth_response.user or not auth_response.session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account",
        )

    user_id = auth_response.user.id

    # Update user profile with role from invitation
    # (profile created by trigger, just need to set role)
    client.table("user_profiles").update(
        {
            "role": invitation["role"],
            "display_name": request.display_name or request.email.split("@")[0],
        }
    ).eq("id", user_id).execute()

    # Mark invitation as accepted
    client.table("invitations").update(
        {
            "status": "accepted",
            "accepted_by": user_id,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", invitation["id"]).execute()

    # Load the profile
    profile_result = client.table("user_profiles").select("*").eq("id", user_id).single().execute()

    logger.info(
        "user_registered",
        user_id=user_id,
        role=invitation["role"],
        inviter_id=invitation["inviter_id"],
    )

    return AuthResponse(
        access_token=auth_response.session.access_token,
        refresh_token=auth_response.session.refresh_token,
        user=UserProfile(
            id=UUID(profile_result.data["id"]),
            role=UserRole(profile_result.data["role"]),
            display_name=profile_result.data.get("display_name"),
            avatar_url=profile_result.data.get("avatar_url"),
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, client: SupabaseDep) -> AuthResponse:
    """Login with email and password."""
    try:
        credentials: SignInWithEmailAndPasswordCredentials = {
            "email": request.email,
            "password": request.password,
        }
        auth_response = client.auth.sign_in_with_password(credentials)
    except Exception as e:
        logger.warning("login_failed", email=request.email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from e

    if not auth_response.user or not auth_response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Load profile
    profile_result = (
        client.table("user_profiles")
        .select("*")
        .eq("id", auth_response.user.id)
        .is_("deleted_at", "null")
        .single()
        .execute()
    )

    if not profile_result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not found",
        )

    logger.info("user_logged_in", user_id=auth_response.user.id)

    return AuthResponse(
        access_token=auth_response.session.access_token,
        refresh_token=auth_response.session.refresh_token,
        user=UserProfile(
            id=UUID(profile_result.data["id"]),
            role=UserRole(profile_result.data["role"]),
            display_name=profile_result.data.get("display_name"),
            avatar_url=profile_result.data.get("avatar_url"),
            swimmer_id=(
                UUID(profile_result.data["swimmer_id"])
                if profile_result.data.get("swimmer_id")
                else None
            ),
        ),
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest, client: SupabaseDep) -> AuthResponse:
    """Refresh access token."""
    try:
        auth_response = client.auth.refresh_session(request.refresh_token)
    except Exception as e:
        logger.warning("refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from e

    if not auth_response.user or not auth_response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Load profile
    profile_result = (
        client.table("user_profiles").select("*").eq("id", auth_response.user.id).single().execute()
    )

    return AuthResponse(
        access_token=auth_response.session.access_token,
        refresh_token=auth_response.session.refresh_token,
        user=UserProfile(
            id=UUID(profile_result.data["id"]),
            role=UserRole(profile_result.data["role"]),
            display_name=profile_result.data.get("display_name"),
            avatar_url=profile_result.data.get("avatar_url"),
        ),
    )


@router.get("/me", response_model=UserProfile)
async def get_me(user: CurrentUser) -> UserProfile:
    """Get current user profile."""
    return user


@router.post("/logout")
async def logout(user: CurrentUser, client: SupabaseDep) -> dict:
    """Logout current user."""
    try:
        client.auth.sign_out()
    except Exception as e:
        logger.warning("logout_error", user_id=str(user.id), error=str(e))

    logger.info("user_logged_out", user_id=str(user.id))
    return {"message": "Logged out"}


# =============================================================================
# INVITATION ENDPOINTS
# =============================================================================


@router.post("/invitations", response_model=Invitation, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    request: InvitationCreate,
    user: CurrentUser,
    client: SupabaseDep,
) -> Invitation:
    """Create an invitation. Role permissions enforced by database trigger."""
    # Check if user can invite this role
    if not user.can_invite_role(request.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot invite users with role: {request.role.value}",
        )

    # Check for existing pending invitation
    existing = (
        client.table("invitations")
        .select("id")
        .eq("email", request.email)
        .eq("status", "pending")
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pending invitation already exists for this email",
        )

    # Create invitation
    data = {
        "inviter_id": str(user.id),
        "email": request.email,
        "role": request.role.value,
    }

    if request.team_id:
        data["team_id"] = str(request.team_id)

    result = client.table("invitations").insert(data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitation",
        )

    row = result.data[0]
    logger.info(
        "invitation_created",
        inviter_id=str(user.id),
        invitee_email=request.email,
        role=request.role.value,
    )

    return Invitation(
        id=UUID(row["id"]),
        inviter_id=UUID(row["inviter_id"]),
        email=row["email"],
        role=UserRole(row["role"]),
        token=row["token"],
        status=InvitationStatus(row["status"]),
        expires_at=row.get("expires_at"),
        team_id=UUID(row["team_id"]) if row.get("team_id") else None,
        created_at=row.get("created_at"),
    )


@router.get("/invitations", response_model=list[Invitation])
async def list_invitations(user: CurrentUser, client: SupabaseDep) -> list[Invitation]:
    """List invitations sent by current user (admins see all)."""
    query = client.table("invitations").select("*").order("created_at", desc=True)

    if not user.is_admin:
        query = query.eq("inviter_id", str(user.id))

    result = query.execute()

    return [
        Invitation(
            id=UUID(row["id"]),
            inviter_id=UUID(row["inviter_id"]),
            email=row["email"],
            role=UserRole(row["role"]),
            token=row["token"] if user.is_admin or row["inviter_id"] == str(user.id) else None,
            status=InvitationStatus(row["status"]),
            expires_at=row.get("expires_at"),
            accepted_by=UUID(row["accepted_by"]) if row.get("accepted_by") else None,
            accepted_at=row.get("accepted_at"),
            team_id=UUID(row["team_id"]) if row.get("team_id") else None,
            created_at=row.get("created_at"),
        )
        for row in result.data
    ]


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: UUID,
    user: CurrentUser,
    client: SupabaseDep,
) -> dict:
    """Revoke a pending invitation."""
    # Get invitation
    result = client.table("invitations").select("*").eq("id", str(invitation_id)).single().execute()

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    invitation = result.data

    # Check permission
    if not user.is_admin and invitation["inviter_id"] != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke another user's invitation",
        )

    if invitation["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revoke invitation with status: {invitation['status']}",
        )

    # Revoke
    client.table("invitations").update({"status": "revoked"}).eq("id", str(invitation_id)).execute()

    logger.info("invitation_revoked", invitation_id=str(invitation_id), user_id=str(user.id))

    return {"message": "Invitation revoked"}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================


@router.get("/users", response_model=list[UserProfile])
async def list_users(admin: AdminUser, client: SupabaseDep) -> list[UserProfile]:
    """List all users (admin only)."""
    result = (
        client.table("user_profiles")
        .select("*")
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )

    return [
        UserProfile(
            id=UUID(row["id"]),
            role=UserRole(row["role"]),
            display_name=row.get("display_name"),
            avatar_url=row.get("avatar_url"),
            swimmer_id=UUID(row["swimmer_id"]) if row.get("swimmer_id") else None,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
        for row in result.data
    ]


class UpdateRoleRequest(BaseModel):
    """Request to update user role."""

    role: UserRole


@router.patch("/users/{user_id}/role", response_model=UserProfile)
async def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    admin: AdminUser,
    client: SupabaseDep,
) -> UserProfile:
    """Update a user's role (admin only)."""
    # Can't change own role
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    result = (
        client.table("user_profiles")
        .update({"role": request.role.value})
        .eq("id", str(user_id))
        .is_("deleted_at", "null")
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    row = result.data[0]
    logger.info(
        "user_role_updated",
        target_user_id=str(user_id),
        new_role=request.role.value,
        admin_id=str(admin.id),
    )

    return UserProfile(
        id=UUID(row["id"]),
        role=UserRole(row["role"]),
        display_name=row.get("display_name"),
        avatar_url=row.get("avatar_url"),
        swimmer_id=UUID(row["swimmer_id"]) if row.get("swimmer_id") else None,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
