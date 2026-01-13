"""Swim time API endpoints.

All endpoints require authentication (invite-only app).
Create, Update require admin or coach role.
Delete requires admin role.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, computed_field, field_validator

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminOrCoachUser, AdminUser, CurrentUser
from swimcuttimes.api.dependencies import SwimTimeDAODep
from swimcuttimes.models.swim_time import Round, SwimTime
from swimcuttimes.models.time_standard import format_centiseconds_to_time

logger = get_logger(__name__)

router = APIRouter(prefix="/times", tags=["times"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================


class SwimTimeCreate(BaseModel):
    """Request body for creating a swim time."""

    swimmer_id: str
    event_id: str
    meet_id: str
    team_id: str
    time_centiseconds: int
    swim_date: date
    suit_id: str | None = None
    round: Round | None = None
    lane: int | None = None
    place: int | None = None
    official: bool = True
    dq: bool = False
    dq_reason: str | None = None

    @field_validator("lane")
    @classmethod
    def validate_lane(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Lane must be between 1 and 10")
        return v


class SwimTimeUpdate(BaseModel):
    """Request body for updating a swim time (partial)."""

    time_centiseconds: int | None = None
    swim_date: date | None = None
    suit_id: str | None = None
    round: Round | None = None
    lane: int | None = None
    place: int | None = None
    official: bool | None = None
    dq: bool | None = None
    dq_reason: str | None = None

    @field_validator("lane")
    @classmethod
    def validate_lane(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Lane must be between 1 and 10")
        return v


class SwimTimeResponse(BaseModel):
    """Response model for swim time."""

    id: str
    swimmer_id: str
    event_id: str
    meet_id: str
    team_id: str
    time_centiseconds: int
    swim_date: date
    suit_id: str | None = None
    round: Round | None = None
    lane: int | None = None
    place: int | None = None
    official: bool = True
    dq: bool = False
    dq_reason: str | None = None

    @computed_field
    @property
    def time_formatted(self) -> str:
        """Format time as MM:SS.cc or SS.cc."""
        return format_centiseconds_to_time(self.time_centiseconds)

    @classmethod
    def from_swim_time(cls, swim_time: SwimTime) -> "SwimTimeResponse":
        """Create response from model."""
        return cls(
            id=swim_time.id,
            swimmer_id=swim_time.swimmer_id,
            event_id=swim_time.event_id,
            meet_id=swim_time.meet_id,
            team_id=swim_time.team_id,
            time_centiseconds=swim_time.time_centiseconds,
            swim_date=swim_time.swim_date,
            suit_id=swim_time.suit_id,
            round=swim_time.round,
            lane=swim_time.lane,
            place=swim_time.place,
            official=swim_time.official,
            dq=swim_time.dq,
            dq_reason=swim_time.dq_reason,
        )


# =============================================================================
# CREATE (Admin or Coach)
# =============================================================================


@router.post("", response_model=SwimTimeResponse, status_code=status.HTTP_201_CREATED)
def create_time(
    data: SwimTimeCreate,
    user: AdminOrCoachUser,
    dao: SwimTimeDAODep,
) -> SwimTimeResponse:
    """Record a new swim time (admin or coach only)."""
    try:
        swim_time = SwimTime(
            swimmer_id=data.swimmer_id,
            event_id=data.event_id,
            meet_id=data.meet_id,
            team_id=data.team_id,
            time_centiseconds=data.time_centiseconds,
            swim_date=data.swim_date,
            suit_id=data.suit_id,
            round=data.round,
            lane=data.lane,
            place=data.place,
            official=data.official,
            dq=data.dq,
            dq_reason=data.dq_reason,
        )
        result = dao.create(swim_time)

        logger.info(
            "swim_time_created",
            time_id=str(result.id),
            swimmer_id=data.swimmer_id,
            event_id=data.event_id,
            time_centiseconds=data.time_centiseconds,
        )
        return SwimTimeResponse.from_swim_time(result)

    except ValueError as e:
        logger.warning("swim_time_create_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("swim_time_create_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create swim time: {e}",
        ) from e


# =============================================================================
# READ - List (Authenticated users)
# =============================================================================


@router.get("", response_model=list[SwimTimeResponse])
def list_times(
    user: CurrentUser,
    dao: SwimTimeDAODep,
    swimmer_id: str | None = Query(None, description="Filter by swimmer"),
    event_id: str | None = Query(None, description="Filter by event"),
    meet_id: str | None = Query(None, description="Filter by meet"),
    team_id: str | None = Query(None, description="Filter by team"),
    round: Round | None = Query(None, description="Filter by round"),
    official_only: bool = Query(True, description="Only include official times"),
    exclude_dq: bool = Query(True, description="Exclude disqualified times"),
    start_date: date | None = Query(None, description="Times after this date"),
    end_date: date | None = Query(None, description="Times before this date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[SwimTimeResponse]:
    """Search swim times with optional filters."""
    results = dao.search(
        swimmer_id=swimmer_id,
        event_id=event_id,
        meet_id=meet_id,
        team_id=team_id,
        round=round,
        official_only=official_only,
        exclude_dq=exclude_dq,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [SwimTimeResponse.from_swim_time(st) for st in results]


# =============================================================================
# READ - Get by ID (Authenticated users)
# =============================================================================


@router.get("/{time_id}", response_model=SwimTimeResponse)
def get_time(
    time_id: str,
    user: CurrentUser,
    dao: SwimTimeDAODep,
) -> SwimTimeResponse:
    """Get a specific swim time by ID."""
    result = dao.get_by_id(time_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")
    return SwimTimeResponse.from_swim_time(result)


# =============================================================================
# UPDATE (Admin or Coach)
# =============================================================================


@router.patch("/{time_id}", response_model=SwimTimeResponse)
def update_time(
    time_id: str,
    data: SwimTimeUpdate,
    user: AdminOrCoachUser,
    dao: SwimTimeDAODep,
) -> SwimTimeResponse:
    """Update a swim time (admin or coach only). Partial update - only provided fields are changed."""
    existing = dao.get_by_id(time_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")

    try:
        updates = data.model_dump(exclude_unset=True)

        # Convert enums to values for database
        if "round" in updates and updates["round"] is not None:
            updates["round"] = updates["round"].value

        result = dao.partial_update(time_id, updates)

        logger.info(
            "swim_time_updated",
            time_id=time_id,
            updated_fields=list(updates.keys()),
        )
        return SwimTimeResponse.from_swim_time(result)

    except ValueError as e:
        logger.warning("swim_time_update_validation_failed", time_id=time_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("swim_time_update_error", time_id=time_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update swim time: {e}",
        ) from e


# =============================================================================
# DELETE (Admin only)
# =============================================================================


@router.delete("/{time_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time(
    time_id: str,
    user: AdminUser,
    dao: SwimTimeDAODep,
) -> None:
    """Delete a swim time (admin only)."""
    existing = dao.get_by_id(time_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")

    try:
        deleted = dao.delete(time_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")

        logger.info(
            "swim_time_deleted",
            time_id=time_id,
            swimmer_id=existing.swimmer_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swim_time_delete_error", time_id=time_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete swim time: {e}",
        ) from e
