"""Fan-swimmer follow relationship endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from swimcuttimes import get_logger
from swimcuttimes.api.auth import CurrentUser
from swimcuttimes.api.dependencies import SupabaseDep
from swimcuttimes.models import FanFollow, FollowRequest, FollowResponse, FollowStatus, UserRole

logger = get_logger(__name__)

router = APIRouter(prefix="/follows", tags=["follows"])


# =============================================================================
# FAN ENDPOINTS
# =============================================================================


@router.post("/request", response_model=FanFollow, status_code=status.HTTP_201_CREATED)
async def request_to_follow(
    request: FollowRequest,
    user: CurrentUser,
    client: SupabaseDep,
) -> FanFollow:
    """Request to follow a swimmer (fan only)."""
    if user.role != UserRole.FAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only fans can request to follow swimmers",
        )

    # Verify target is a swimmer
    swimmer_result = (
        client.table("user_profiles")
        .select("id, role")
        .eq("id", str(request.swimmer_id))
        .is_("deleted_at", "null")
        .single()
        .execute()
    )

    if not swimmer_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    if swimmer_result.data["role"] != "swimmer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only follow users with role: swimmer",
        )

    # Check for existing relationship
    existing = (
        client.table("fan_follows")
        .select("id, status")
        .eq("fan_id", str(user.id))
        .eq("swimmer_id", str(request.swimmer_id))
        .execute()
    )

    if existing.data:
        existing_status = existing.data[0]["status"]
        if existing_status == "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already following this swimmer",
            )
        if existing_status == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Follow request already pending",
            )

    # Create follow request
    result = (
        client.table("fan_follows")
        .insert(
            {
                "fan_id": str(user.id),
                "swimmer_id": str(request.swimmer_id),
                "initiated_by": str(user.id),
                "status": "pending",
            }
        )
        .execute()
    )

    row = result.data[0]
    logger.info(
        "follow_requested",
        fan_id=str(user.id),
        swimmer_id=str(request.swimmer_id),
    )

    return FanFollow(
        id=UUID(row["id"]),
        fan_id=UUID(row["fan_id"]),
        swimmer_id=UUID(row["swimmer_id"]),
        initiated_by=UUID(row["initiated_by"]),
        status=FollowStatus(row["status"]),
        created_at=row.get("created_at"),
    )


@router.get("/following", response_model=list[FanFollow])
async def list_following(user: CurrentUser, client: SupabaseDep) -> list[FanFollow]:
    """List swimmers the current fan is following."""
    if user.role != UserRole.FAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for fans only",
        )

    result = (
        client.table("fan_follows")
        .select("*")
        .eq("fan_id", str(user.id))
        .order("created_at", desc=True)
        .execute()
    )

    return [
        FanFollow(
            id=UUID(row["id"]),
            fan_id=UUID(row["fan_id"]),
            swimmer_id=UUID(row["swimmer_id"]),
            initiated_by=UUID(row["initiated_by"]),
            status=FollowStatus(row["status"]),
            created_at=row.get("created_at"),
            responded_at=row.get("responded_at"),
        )
        for row in result.data
    ]


@router.delete("/{follow_id}")
async def unfollow(
    follow_id: UUID,
    user: CurrentUser,
    client: SupabaseDep,
) -> dict:
    """Unfollow a swimmer or cancel pending request."""
    result = client.table("fan_follows").select("*").eq("id", str(follow_id)).single().execute()

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow not found")

    follow = result.data

    # Check permission: fan can unfollow, swimmer can remove follower, admin can do both
    is_fan = follow["fan_id"] == str(user.id)
    is_swimmer = follow["swimmer_id"] == str(user.id)
    if not is_fan and not is_swimmer and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify this follow relationship",
        )

    client.table("fan_follows").delete().eq("id", str(follow_id)).execute()

    logger.info(
        "follow_removed",
        follow_id=str(follow_id),
        fan_id=follow["fan_id"],
        swimmer_id=follow["swimmer_id"],
        removed_by=str(user.id),
    )

    return {"message": "Unfollowed"}


# =============================================================================
# SWIMMER ENDPOINTS
# =============================================================================


@router.get("/followers", response_model=list[FanFollow])
async def list_followers(user: CurrentUser, client: SupabaseDep) -> list[FanFollow]:
    """List fans following the current swimmer."""
    if user.role != UserRole.SWIMMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for swimmers only",
        )

    result = (
        client.table("fan_follows")
        .select("*")
        .eq("swimmer_id", str(user.id))
        .order("created_at", desc=True)
        .execute()
    )

    return [
        FanFollow(
            id=UUID(row["id"]),
            fan_id=UUID(row["fan_id"]),
            swimmer_id=UUID(row["swimmer_id"]),
            initiated_by=UUID(row["initiated_by"]),
            status=FollowStatus(row["status"]),
            created_at=row.get("created_at"),
            responded_at=row.get("responded_at"),
        )
        for row in result.data
    ]


@router.get("/requests", response_model=list[FanFollow])
async def list_follow_requests(user: CurrentUser, client: SupabaseDep) -> list[FanFollow]:
    """List pending follow requests for the current swimmer."""
    if user.role != UserRole.SWIMMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for swimmers only",
        )

    result = (
        client.table("fan_follows")
        .select("*")
        .eq("swimmer_id", str(user.id))
        .eq("status", "pending")
        .neq("initiated_by", str(user.id))  # Only requests from fans, not own invites
        .order("created_at", desc=True)
        .execute()
    )

    return [
        FanFollow(
            id=UUID(row["id"]),
            fan_id=UUID(row["fan_id"]),
            swimmer_id=UUID(row["swimmer_id"]),
            initiated_by=UUID(row["initiated_by"]),
            status=FollowStatus(row["status"]),
            created_at=row.get("created_at"),
        )
        for row in result.data
    ]


@router.post("/{follow_id}/respond", response_model=FanFollow)
async def respond_to_follow(
    follow_id: UUID,
    response: FollowResponse,
    user: CurrentUser,
    client: SupabaseDep,
) -> FanFollow:
    """Respond to a follow request (swimmer approves/denies) or invite (fan accepts/declines)."""
    result = (
        client.table("fan_follows")
        .select("*")
        .eq("id", str(follow_id))
        .eq("status", "pending")
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending follow request not found",
        )

    follow = result.data

    # Determine who can respond
    # - If fan initiated (request): swimmer responds
    # - If swimmer initiated (invite): fan responds
    if follow["initiated_by"] == follow["fan_id"]:
        # Fan requested, swimmer must respond
        if follow["swimmer_id"] != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the swimmer can respond to this request",
            )
    else:
        # Swimmer invited, fan must respond
        if follow["fan_id"] != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the fan can respond to this invite",
            )

    new_status = "approved" if response.approved else "denied"

    update_result = (
        client.table("fan_follows")
        .update({"status": new_status, "responded_at": "now()"})
        .eq("id", str(follow_id))
        .execute()
    )

    row = update_result.data[0]

    logger.info(
        "follow_responded",
        follow_id=str(follow_id),
        status=new_status,
        responder_id=str(user.id),
    )

    return FanFollow(
        id=UUID(row["id"]),
        fan_id=UUID(row["fan_id"]),
        swimmer_id=UUID(row["swimmer_id"]),
        initiated_by=UUID(row["initiated_by"]),
        status=FollowStatus(row["status"]),
        created_at=row.get("created_at"),
        responded_at=row.get("responded_at"),
    )


@router.post("/invite", response_model=FanFollow, status_code=status.HTTP_201_CREATED)
async def invite_fan(
    request: FollowRequest,  # Reusing, but fan_id instead of swimmer_id
    user: CurrentUser,
    client: SupabaseDep,
) -> FanFollow:
    """Invite a fan to follow (swimmer only). Uses swimmer_id field as fan_id."""
    if user.role != UserRole.SWIMMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only swimmers can invite fans",
        )

    fan_id = request.swimmer_id  # Reusing the field

    # Verify target is a fan
    fan_result = (
        client.table("user_profiles")
        .select("id, role")
        .eq("id", str(fan_id))
        .is_("deleted_at", "null")
        .single()
        .execute()
    )

    if not fan_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fan not found")

    if fan_result.data["role"] != "fan":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only invite users with role: fan",
        )

    # Check for existing relationship
    existing = (
        client.table("fan_follows")
        .select("id, status")
        .eq("fan_id", str(fan_id))
        .eq("swimmer_id", str(user.id))
        .execute()
    )

    if existing.data:
        existing_status = existing.data[0]["status"]
        if existing_status == "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This fan is already following you",
            )
        if existing_status == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invite already pending",
            )

    # Create invite
    result = (
        client.table("fan_follows")
        .insert(
            {
                "fan_id": str(fan_id),
                "swimmer_id": str(user.id),
                "initiated_by": str(user.id),
                "status": "pending",
            }
        )
        .execute()
    )

    row = result.data[0]
    logger.info(
        "fan_invited",
        swimmer_id=str(user.id),
        fan_id=str(fan_id),
    )

    return FanFollow(
        id=UUID(row["id"]),
        fan_id=UUID(row["fan_id"]),
        swimmer_id=UUID(row["swimmer_id"]),
        initiated_by=UUID(row["initiated_by"]),
        status=FollowStatus(row["status"]),
        created_at=row.get("created_at"),
    )
