"""Meet API endpoints.

All endpoints require authentication (invite-only app).
Create, Update, Delete require admin role.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminUser, CurrentUser
from swimcuttimes.api.dependencies import MeetDAODep
from swimcuttimes.models.event import Course
from swimcuttimes.models.meet import Meet, MeetType

logger = get_logger(__name__)

router = APIRouter(prefix="/meets", tags=["meets"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================


class MeetCreate(BaseModel):
    """Request body for creating a meet."""

    name: str
    location: str
    city: str
    state: str | None = None
    country: str = "USA"
    start_date: date
    end_date: date | None = None
    course: Course
    lanes: int = 8
    indoor: bool = True
    sanctioning_body: str
    meet_type: MeetType


class MeetUpdate(BaseModel):
    """Request body for updating a meet (partial)."""

    name: str | None = None
    location: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    course: Course | None = None
    lanes: int | None = None
    indoor: bool | None = None
    sanctioning_body: str | None = None
    meet_type: MeetType | None = None


# =============================================================================
# CREATE (Admin only)
# =============================================================================


@router.post("", response_model=Meet, status_code=status.HTTP_201_CREATED)
def create_meet(
    data: MeetCreate,
    user: AdminUser,
    dao: MeetDAODep,
) -> Meet:
    """Create a new meet (admin only)."""
    try:
        meet = Meet(
            name=data.name,
            location=data.location,
            city=data.city,
            state=data.state,
            country=data.country,
            start_date=data.start_date,
            end_date=data.end_date,
            course=data.course,
            lanes=data.lanes,
            indoor=data.indoor,
            sanctioning_body=data.sanctioning_body,
            meet_type=data.meet_type,
        )
        result = dao.create(meet)

        logger.info(
            "meet_created",
            meet_id=str(result.id),
            meet_name=data.name,
            meet_type=data.meet_type.value,
        )
        return result

    except ValueError as e:
        logger.warning("meet_create_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        error_str = str(e).lower()
        if "duplicate" in error_str or "unique" in error_str:
            logger.warning("meet_create_duplicate", meet_name=data.name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A meet named '{data.name}' already exists",
            ) from e
        logger.error("meet_create_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create meet: {e}",
        ) from e


# =============================================================================
# READ - List (Authenticated users)
# =============================================================================


@router.get("", response_model=list[Meet])
def list_meets(
    user: CurrentUser,
    dao: MeetDAODep,
    name: str | None = Query(None, description="Partial name match"),
    course: Course | None = None,
    meet_type: MeetType | None = None,
    sanctioning_body: str | None = Query(None, description="e.g., 'NE Swimming', 'USA Swimming'"),
    start_after: date | None = Query(None, description="Meets starting after this date"),
    start_before: date | None = Query(None, description="Meets starting before this date"),
    indoor: bool | None = Query(None, description="Filter by indoor/outdoor"),
    limit: int = Query(100, ge=1, le=500),
) -> list[Meet]:
    """Search meets with optional filters."""
    return dao.search(
        name=name,
        course=course,
        meet_type=meet_type,
        sanctioning_body=sanctioning_body,
        start_after=start_after,
        start_before=start_before,
        indoor=indoor,
        limit=limit,
    )


# =============================================================================
# READ - Get by ID (Authenticated users)
# =============================================================================


@router.get("/{meet_id}", response_model=Meet)
def get_meet(
    meet_id: str,
    user: CurrentUser,
    dao: MeetDAODep,
) -> Meet:
    """Get a specific meet by ID."""
    result = dao.get_by_id(meet_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")
    return result


# =============================================================================
# UPDATE (Admin only)
# =============================================================================


@router.patch("/{meet_id}", response_model=Meet)
def update_meet(
    meet_id: str,
    data: MeetUpdate,
    user: AdminUser,
    dao: MeetDAODep,
) -> Meet:
    """Update a meet (admin only). Partial update - only provided fields are changed."""
    existing = dao.get_by_id(meet_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")

    try:
        updates = data.model_dump(exclude_unset=True)

        # Convert enums to values for database
        if "course" in updates and updates["course"] is not None:
            updates["course"] = updates["course"].value
        if "meet_type" in updates and updates["meet_type"] is not None:
            updates["meet_type"] = updates["meet_type"].value

        result = dao.partial_update(meet_id, updates)

        logger.info(
            "meet_updated",
            meet_id=meet_id,
            updated_fields=list(updates.keys()),
        )
        return result

    except ValueError as e:
        logger.warning("meet_update_validation_failed", meet_id=meet_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        if "duplicate" in error_str or "unique" in error_str:
            logger.warning("meet_update_duplicate", meet_id=meet_id, new_name=data.name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A meet named '{data.name}' already exists",
            ) from e
        logger.error("meet_update_error", meet_id=meet_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update meet: {e}",
        ) from e


# =============================================================================
# DELETE (Admin only)
# =============================================================================


@router.delete("/{meet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meet(
    meet_id: str,
    user: AdminUser,
    dao: MeetDAODep,
) -> None:
    """Delete a meet (admin only)."""
    existing = dao.get_by_id(meet_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")

    try:
        deleted = dao.delete(meet_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")

        logger.info(
            "meet_deleted",
            meet_id=meet_id,
            meet_name=existing.name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("meet_delete_error", meet_id=meet_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete meet: {e}",
        ) from e
