"""Time standards API endpoints.

All endpoints require authentication (invite-only app).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from swimcuttimes.api.auth import AdminUser, CurrentUser
from swimcuttimes.api.dependencies import TimeStandardDAODep
from swimcuttimes.models import Course, Gender, Stroke, TimeStandard

router = APIRouter(prefix="/time-standards", tags=["time-standards"])


class EventCreate(BaseModel):
    """Event data for creating a time standard."""

    stroke: Stroke
    distance: int
    course: Course


class TimeStandardCreate(BaseModel):
    """Request body for creating a time standard."""

    event: EventCreate
    gender: Gender
    age_group: str | None = None
    standard_name: str
    cut_level: str
    sanctioning_body: str
    time_centiseconds: int
    effective_year: int


@router.post("", response_model=TimeStandard, status_code=status.HTTP_201_CREATED)
def create_time_standard(
    data: TimeStandardCreate,
    user: AdminUser,  # Admin only
    dao: TimeStandardDAODep,
) -> TimeStandard:
    """Create a new time standard (admin only)."""
    from swimcuttimes import get_logger

    logger = get_logger(__name__)

    try:
        result = dao.create_with_event(
            stroke=data.event.stroke,
            distance=data.event.distance,
            course=data.event.course,
            gender=data.gender,
            age_group=data.age_group,
            standard_name=data.standard_name,
            cut_level=data.cut_level,
            sanctioning_body=data.sanctioning_body,
            time_centiseconds=data.time_centiseconds,
            effective_year=data.effective_year,
        )
        logger.info(
            "time_standard_created",
            swim_event=f"{data.event.distance} {data.event.stroke} {data.event.course}",
            standard=data.standard_name,
        )
        return result
    except ValueError as e:
        logger.warning(
            "time_standard_create_failed",
            error=str(e),
            swim_event=f"{data.event.distance} {data.event.stroke} {data.event.course}",
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            "time_standard_create_error",
            error=str(e),
            swim_event=f"{data.event.distance} {data.event.stroke} {data.event.course}",
        )
        raise HTTPException(status_code=500, detail=f"Failed to create time standard: {e}") from e


@router.get("", response_model=list[TimeStandard])
def list_time_standards(
    user: CurrentUser,  # Requires auth
    dao: TimeStandardDAODep,
    gender: Gender | None = None,
    stroke: Stroke | None = None,
    course: Course | None = None,
    distance: int | None = None,
    age_group: str | None = Query(None, description="e.g., '15-18', '10-under', 'Open'"),
    sanctioning_body: str | None = Query(None, description="e.g., 'USA Swimming'"),
    limit: int = Query(100, ge=1, le=500),
) -> list[TimeStandard]:
    """Search time standards with optional filters."""
    return dao.search(
        gender=gender,
        stroke=stroke,
        course=course,
        distance=distance,
        age_group=age_group,
        sanctioning_body=sanctioning_body,
        limit=limit,
    )


@router.get("/by-body/{sanctioning_body}", response_model=list[TimeStandard])
def get_by_sanctioning_body(
    sanctioning_body: str,
    user: CurrentUser,  # Requires auth
    dao: TimeStandardDAODep,
    limit: int = Query(100, ge=1, le=500),
) -> list[TimeStandard]:
    """Get all time standards for a specific sanctioning body."""
    results = dao.find_by_sanctioning_body(sanctioning_body, limit=limit)
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No time standards found for '{sanctioning_body}'",
        )
    return results


@router.get("/{time_standard_id}", response_model=TimeStandard)
def get_time_standard(
    time_standard_id: UUID,
    user: CurrentUser,  # Requires auth
    dao: TimeStandardDAODep,
) -> TimeStandard:
    """Get a specific time standard by ID."""
    result = dao.get(time_standard_id)
    if not result:
        raise HTTPException(status_code=404, detail="Time standard not found")
    return result
