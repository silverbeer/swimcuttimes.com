"""User profile and authentication models."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRole(StrEnum):
    """User roles with hierarchical permissions.

    Permission hierarchy:
        admin  → can invite: coach, swimmer, fan
        coach  → can invite: swimmer, fan
        swimmer → can invite: fan
        fan    → cannot invite anyone
    """

    ADMIN = "admin"
    COACH = "coach"
    SWIMMER = "swimmer"
    FAN = "fan"


class InvitationStatus(StrEnum):
    """Status of an invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class FollowStatus(StrEnum):
    """Status of a fan-swimmer follow relationship."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class UserProfile(BaseModel):
    """User profile extending Supabase auth."""

    id: UUID  # Same as auth.users.id (1:1 relationship, stays UUID)
    role: UserRole = UserRole.FAN
    display_name: str | None = None
    avatar_url: str | None = None
    swimmer_id: str | None = None  # Link to swimmer record (short ID)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_coach(self) -> bool:
        return self.role == UserRole.COACH

    @property
    def is_swimmer(self) -> bool:
        return self.role == UserRole.SWIMMER

    @property
    def is_fan(self) -> bool:
        return self.role == UserRole.FAN

    def can_invite_role(self, role: UserRole) -> bool:
        """Check if this user can invite someone with the given role."""
        if self.role == UserRole.ADMIN:
            return True
        if self.role == UserRole.COACH:
            return role in (UserRole.SWIMMER, UserRole.FAN)
        if self.role == UserRole.SWIMMER:
            return role == UserRole.FAN
        return False


class Invitation(BaseModel):
    """Invitation for new user registration."""

    id: str | None = None  # Short ID
    inviter_id: UUID  # References auth.users (stays UUID)
    email: EmailStr
    role: UserRole
    token: str | None = None  # Only visible to inviter/admin
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: datetime | None = None
    accepted_by: UUID | None = None  # References auth.users (stays UUID)
    accepted_at: datetime | None = None
    team_id: str | None = None  # References teams (short ID)
    created_at: datetime | None = None


class InvitationCreate(BaseModel):
    """Request to create an invitation."""

    email: EmailStr
    role: UserRole
    team_id: str | None = None  # References teams (short ID)


class FanFollow(BaseModel):
    """Fan-swimmer follow relationship."""

    id: str | None = None  # Short ID
    fan_id: UUID  # References auth.users (stays UUID)
    swimmer_id: str  # References swimmers (short ID)
    initiated_by: UUID  # References auth.users (stays UUID)
    status: FollowStatus = FollowStatus.PENDING
    created_at: datetime | None = None
    responded_at: datetime | None = None

    @property
    def is_request(self) -> bool:
        """True if fan requested to follow."""
        return self.initiated_by == self.fan_id

    @property
    def is_invite(self) -> bool:
        """True if swimmer invited the fan."""
        return self.initiated_by == self.swimmer_id


class FollowRequest(BaseModel):
    """Request from fan to follow a swimmer."""

    swimmer_id: str  # References swimmers (short ID)


class FollowInvite(BaseModel):
    """Invite from swimmer to a fan."""

    fan_id: UUID


class FollowResponse(BaseModel):
    """Response to a follow request/invite."""

    approved: bool
