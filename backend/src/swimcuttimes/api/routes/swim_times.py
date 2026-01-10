"""Swim time API endpoints.

All endpoints require authentication (invite-only app).
Create, Update require admin or coach role.
Delete requires admin or coach role.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminOrCoachUser, CurrentUser
from swimcuttimes.api.dependencies import (
    EventDAODep,
    MeetDAODep,
    SwimmerDAODep,
    SwimTimeDAODep,
    TeamDAODep,
)
from swimcuttimes.models import SwimTime
from swimcuttimes.models.swim_time import Round
from swimcuttimes.models.time_standard import (
    format_centiseconds_to_time,
    parse_time_to_centiseconds,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/swim-times", tags=["swim-times"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================


class SwimTimeCreate(BaseModel):
    """Request body for recording a swim time."""

    swimmer_id: UUID
    event_id: UUID
    meet_id: UUID
    team_id: UUID
    time_centiseconds: int | None = None  # Either this or time_formatted
    time_formatted: str | None = None  # e.g., "1:05.23" or "32.45"
    swim_date: date
    round: Round | None = None
    lane: int | None = None
    place: int | None = None
    official: bool = True
    dq: bool = False
    dq_reason: str | None = None


class SwimTimeUpdate(BaseModel):
    """Request body for updating a swim time (partial)."""

    time_centiseconds: int | None = None
    time_formatted: str | None = None
    swim_date: date | None = None
    round: Round | None = None
    lane: int | None = None
    place: int | None = None
    official: bool | None = None
    dq: bool | None = None
    dq_reason: str | None = None


class SwimTimeResponse(BaseModel):
    """Response for a swim time with formatted time."""

    id: UUID
    swimmer_id: UUID
    event_id: UUID
    meet_id: UUID
    team_id: UUID
    time_centiseconds: int
    time_formatted: str
    swim_date: date
    round: Round | None = None
    lane: int | None = None
    place: int | None = None
    official: bool
    dq: bool
    dq_reason: str | None = None

    @classmethod
    def from_swim_time(cls, st: SwimTime) -> "SwimTimeResponse":
        return cls(
            id=st.id,
            swimmer_id=st.swimmer_id,
            event_id=st.event_id,
            meet_id=st.meet_id,
            team_id=st.team_id,
            time_centiseconds=st.time_centiseconds,
            time_formatted=st.time_formatted,
            swim_date=st.swim_date,
            round=st.round,
            lane=st.lane,
            place=st.place,
            official=st.official,
            dq=st.dq,
            dq_reason=st.dq_reason,
        )


class SwimTimeWithAnalysis(SwimTimeResponse):
    """Response with personal best comparison."""

    personal_best: SwimTimeResponse | None = None
    is_personal_best: bool = False
    time_off_pb: float | None = None  # seconds difference (positive = slower)
    improvement_percentage: float | None = None


# =============================================================================
# CREATE (Admin or Coach)
# =============================================================================


@router.post("", response_model=SwimTimeResponse, status_code=status.HTTP_201_CREATED)
def record_swim_time(
    data: SwimTimeCreate,
    user: AdminOrCoachUser,
    swim_time_dao: SwimTimeDAODep,
    swimmer_dao: SwimmerDAODep,
    event_dao: EventDAODep,
    meet_dao: MeetDAODep,
    team_dao: TeamDAODep,
) -> SwimTimeResponse:
    """Record a swim time (admin or coach only)."""
    # Validate references exist
    if not swimmer_dao.get_by_id(data.swimmer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")
    if not event_dao.get_by_id(data.event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if not meet_dao.get_by_id(data.meet_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")
    if not team_dao.get_by_id(data.team_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Parse time - either centiseconds or formatted
    time_cs = data.time_centiseconds
    if time_cs is None and data.time_formatted:
        try:
            time_cs = parse_time_to_centiseconds(data.time_formatted)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time format: {e}",
            ) from e
    elif time_cs is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either time_centiseconds or time_formatted is required",
        )

    try:
        swim_time = SwimTime(
            swimmer_id=data.swimmer_id,
            event_id=data.event_id,
            meet_id=data.meet_id,
            team_id=data.team_id,
            time_centiseconds=time_cs,
            swim_date=data.swim_date,
            round=data.round,
            lane=data.lane,
            place=data.place,
            official=data.official,
            dq=data.dq,
            dq_reason=data.dq_reason,
        )
        result = swim_time_dao.create(swim_time)

        logger.info(
            "swim_time_recorded",
            swim_time_id=str(result.id),
            swimmer_id=str(data.swimmer_id),
            event_id=str(data.event_id),
            time=format_centiseconds_to_time(time_cs),
        )
        return SwimTimeResponse.from_swim_time(result)

    except ValueError as e:
        logger.warning("swim_time_create_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("swim_time_create_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record swim time: {e}",
        ) from e


# =============================================================================
# READ - List (Authenticated users)
# =============================================================================


@router.get("", response_model=list[SwimTimeResponse])
def list_swim_times(
    user: CurrentUser,
    swim_time_dao: SwimTimeDAODep,
    swimmer_id: UUID | None = Query(None, description="Filter by swimmer"),
    event_id: UUID | None = Query(None, description="Filter by event"),
    meet_id: UUID | None = Query(None, description="Filter by meet"),
    team_id: UUID | None = Query(None, description="Filter by team"),
    round: Round | None = Query(None, description="Filter by round"),
    official_only: bool = Query(True, description="Only official times"),
    exclude_dq: bool = Query(True, description="Exclude DQ'd times"),
    start_date: date | None = Query(None, description="Only times after this date"),
    end_date: date | None = Query(None, description="Only times before this date"),
    limit: int = Query(100, ge=1, le=500),
) -> list[SwimTimeResponse]:
    """Search swim times with optional filters."""
    times = swim_time_dao.search(
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
    return [SwimTimeResponse.from_swim_time(t) for t in times]


# =============================================================================
# READ - Get by ID (Authenticated users)
# =============================================================================


@router.get("/{swim_time_id}", response_model=SwimTimeResponse)
def get_swim_time(
    swim_time_id: UUID,
    user: CurrentUser,
    swim_time_dao: SwimTimeDAODep,
) -> SwimTimeResponse:
    """Get a specific swim time by ID."""
    result = swim_time_dao.get_by_id(swim_time_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")
    return SwimTimeResponse.from_swim_time(result)


# =============================================================================
# UPDATE (Admin or Coach)
# =============================================================================


@router.patch("/{swim_time_id}", response_model=SwimTimeResponse)
def update_swim_time(
    swim_time_id: UUID,
    data: SwimTimeUpdate,
    user: AdminOrCoachUser,
    swim_time_dao: SwimTimeDAODep,
) -> SwimTimeResponse:
    """Update a swim time (admin or coach only). Partial update."""
    existing = swim_time_dao.get_by_id(swim_time_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")

    try:
        updates = data.model_dump(exclude_unset=True)

        # Handle time_formatted conversion
        if "time_formatted" in updates and updates["time_formatted"]:
            try:
                updates["time_centiseconds"] = parse_time_to_centiseconds(updates["time_formatted"])
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid time format: {e}",
                ) from e
            del updates["time_formatted"]
        elif "time_formatted" in updates:
            del updates["time_formatted"]

        result = swim_time_dao.partial_update(swim_time_id, updates)

        logger.info(
            "swim_time_updated",
            swim_time_id=str(swim_time_id),
            updated_fields=list(updates.keys()),
        )
        return SwimTimeResponse.from_swim_time(result)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "swim_time_update_validation_failed", swim_time_id=str(swim_time_id), error=str(e)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("swim_time_update_error", swim_time_id=str(swim_time_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update swim time: {e}",
        ) from e


# =============================================================================
# DELETE (Admin or Coach)
# =============================================================================


@router.delete("/{swim_time_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_swim_time(
    swim_time_id: UUID,
    user: AdminOrCoachUser,
    swim_time_dao: SwimTimeDAODep,
) -> None:
    """Delete a swim time (admin or coach only)."""
    existing = swim_time_dao.get_by_id(swim_time_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")

    try:
        deleted = swim_time_dao.delete(swim_time_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")

        logger.info(
            "swim_time_deleted",
            swim_time_id=str(swim_time_id),
            swimmer_id=str(existing.swimmer_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swim_time_delete_error", swim_time_id=str(swim_time_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete swim time: {e}",
        ) from e


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================


@router.get("/analysis/{swim_time_id}", response_model=SwimTimeWithAnalysis)
def analyze_swim_time(
    swim_time_id: UUID,
    user: CurrentUser,
    swim_time_dao: SwimTimeDAODep,
) -> SwimTimeWithAnalysis:
    """Analyze a swim time compared to personal best."""
    time = swim_time_dao.get_by_id(swim_time_id)
    if not time:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swim time not found")

    pb = swim_time_dao.find_personal_best(time.swimmer_id, time.event_id)

    is_pb = pb is not None and time.id == pb.id
    time_off = None
    improvement_pct = None

    if pb and not is_pb:
        time_off = (time.time_centiseconds - pb.time_centiseconds) / 100
        if pb.time_centiseconds > 0:
            diff = pb.time_centiseconds - time.time_centiseconds
            improvement_pct = (diff / pb.time_centiseconds) * 100

    return SwimTimeWithAnalysis(
        id=time.id,
        swimmer_id=time.swimmer_id,
        event_id=time.event_id,
        meet_id=time.meet_id,
        team_id=time.team_id,
        time_centiseconds=time.time_centiseconds,
        time_formatted=time.time_formatted,
        swim_date=time.swim_date,
        round=time.round,
        lane=time.lane,
        place=time.place,
        official=time.official,
        dq=time.dq,
        dq_reason=time.dq_reason,
        personal_best=SwimTimeResponse.from_swim_time(pb) if pb else None,
        is_personal_best=is_pb,
        time_off_pb=time_off,
        improvement_percentage=improvement_pct,
    )


# =============================================================================
# PERSONAL BESTS (on swimmers router scope but defined here)
# =============================================================================

# Note: We create a separate router for swimmer-related endpoints
swimmers_router = APIRouter(prefix="/swimmers", tags=["swimmers"])


@swimmers_router.get("/{swimmer_id}/personal-bests", response_model=list[SwimTimeResponse])
def get_swimmer_personal_bests(
    swimmer_id: UUID,
    user: CurrentUser,
    swim_time_dao: SwimTimeDAODep,
    swimmer_dao: SwimmerDAODep,
) -> list[SwimTimeResponse]:
    """Get all personal bests for a swimmer (one per event)."""
    # Verify swimmer exists
    if not swimmer_dao.get_by_id(swimmer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    times = swim_time_dao.find_all_personal_bests(swimmer_id)
    return [SwimTimeResponse.from_swim_time(t) for t in times]
