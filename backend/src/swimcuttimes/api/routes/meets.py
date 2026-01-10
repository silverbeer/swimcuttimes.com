"""Meet API endpoints.

All endpoints require authentication (invite-only app).
Create, Update require admin or coach role.
Delete requires admin role.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminOrCoachUser, AdminUser, CurrentUser
from swimcuttimes.api.dependencies import MeetDAODep, MeetTeamDAODep, TeamDAODep
from swimcuttimes.models import Meet, MeetTeam, MeetType
from swimcuttimes.models.event import Course

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
    lanes: int = 6
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


class MeetTeamCreate(BaseModel):
    """Request body for adding a team to a meet."""

    team_id: UUID
    is_host: bool = False


class MeetTeamResponse(BaseModel):
    """Response for a team in a meet."""

    id: UUID
    meet_id: UUID
    team_id: UUID
    team_name: str
    is_host: bool


# =============================================================================
# CREATE (Admin or Coach)
# =============================================================================


@router.post("", response_model=Meet, status_code=status.HTTP_201_CREATED)
def create_meet(
    data: MeetCreate,
    user: AdminOrCoachUser,
    dao: MeetDAODep,
) -> Meet:
    """Create a new meet (admin or coach only)."""
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
    sanctioning_body: str | None = Query(None, description="e.g., 'USA Swimming', 'MIAA'"),
    start_after: date | None = Query(None, description="Only meets starting after this date"),
    start_before: date | None = Query(None, description="Only meets starting before this date"),
    indoor: bool | None = None,
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
    meet_id: UUID,
    user: CurrentUser,
    dao: MeetDAODep,
) -> Meet:
    """Get a specific meet by ID."""
    result = dao.get_by_id(meet_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")
    return result


# =============================================================================
# UPDATE (Admin or Coach)
# =============================================================================


@router.patch("/{meet_id}", response_model=Meet)
def update_meet(
    meet_id: UUID,
    data: MeetUpdate,
    user: AdminOrCoachUser,
    dao: MeetDAODep,
) -> Meet:
    """Update a meet (admin or coach only). Partial update - only provided fields are changed."""
    existing = dao.get_by_id(meet_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")

    try:
        # Build update dict
        updates = data.model_dump(exclude_unset=True)

        # Validate lanes if being updated
        if "lanes" in updates and updates["lanes"] not in (6, 8, 10):
            raise ValueError("Lanes must be 6, 8, or 10")

        result = dao.partial_update(meet_id, updates)

        logger.info(
            "meet_updated",
            meet_id=str(meet_id),
            updated_fields=list(updates.keys()),
        )
        return result

    except ValueError as e:
        logger.warning("meet_update_validation_failed", meet_id=str(meet_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        if "duplicate" in error_str or "unique" in error_str:
            logger.warning("meet_update_duplicate", meet_id=str(meet_id), new_name=data.name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A meet named '{data.name}' already exists",
            ) from e
        logger.error("meet_update_error", meet_id=str(meet_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update meet: {e}",
        ) from e


# =============================================================================
# DELETE (Admin only)
# =============================================================================


@router.delete("/{meet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meet(
    meet_id: UUID,
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
            meet_id=str(meet_id),
            meet_name=existing.name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("meet_delete_error", meet_id=str(meet_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete meet: {e}",
        ) from e


# =============================================================================
# MEET-TEAM ASSOCIATIONS
# =============================================================================


@router.post(
    "/{meet_id}/teams", response_model=MeetTeamResponse, status_code=status.HTTP_201_CREATED
)
def add_team_to_meet(
    meet_id: UUID,
    data: MeetTeamCreate,
    user: AdminOrCoachUser,
    meet_dao: MeetDAODep,
    meet_team_dao: MeetTeamDAODep,
    team_dao: TeamDAODep,
) -> MeetTeamResponse:
    """Add a team to a meet (admin or coach only)."""
    # Verify meet exists
    meet = meet_dao.get_by_id(meet_id)
    if not meet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")

    # Verify team exists
    team = team_dao.get_by_id(data.team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Check if team already in meet
    if meet_team_dao.is_team_in_meet(meet_id, data.team_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team '{team.name}' is already in this meet",
        )

    try:
        meet_team = MeetTeam(
            meet_id=meet_id,
            team_id=data.team_id,
            is_host=data.is_host,
        )
        result = meet_team_dao.create(meet_team)

        logger.info(
            "team_added_to_meet",
            meet_id=str(meet_id),
            team_id=str(data.team_id),
            is_host=data.is_host,
        )

        return MeetTeamResponse(
            id=result.id,
            meet_id=result.meet_id,
            team_id=result.team_id,
            team_name=team.name,
            is_host=result.is_host,
        )

    except Exception as e:
        logger.error("add_team_to_meet_error", meet_id=str(meet_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add team to meet: {e}",
        ) from e


@router.get("/{meet_id}/teams", response_model=list[MeetTeamResponse])
def list_meet_teams(
    meet_id: UUID,
    user: CurrentUser,
    meet_dao: MeetDAODep,
    meet_team_dao: MeetTeamDAODep,
    team_dao: TeamDAODep,
) -> list[MeetTeamResponse]:
    """List all teams participating in a meet."""
    # Verify meet exists
    meet = meet_dao.get_by_id(meet_id)
    if not meet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")

    meet_teams = meet_team_dao.find_by_meet(meet_id)

    # Build response with team names
    result = []
    for mt in meet_teams:
        team = team_dao.get_by_id(mt.team_id)
        if team:
            result.append(
                MeetTeamResponse(
                    id=mt.id,
                    meet_id=mt.meet_id,
                    team_id=mt.team_id,
                    team_name=team.name,
                    is_host=mt.is_host,
                )
            )

    return result


@router.delete("/{meet_id}/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_from_meet(
    meet_id: UUID,
    team_id: UUID,
    user: AdminOrCoachUser,
    meet_dao: MeetDAODep,
    meet_team_dao: MeetTeamDAODep,
) -> None:
    """Remove a team from a meet (admin or coach only)."""
    # Verify meet exists
    meet = meet_dao.get_by_id(meet_id)
    if not meet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meet not found")

    # Find the meet-team association
    meet_team = meet_team_dao.find_by_meet_and_team(meet_id, team_id)
    if not meet_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team is not in this meet",
        )

    try:
        deleted = meet_team_dao.delete(meet_team.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove team from meet",
            )

        logger.info(
            "team_removed_from_meet",
            meet_id=str(meet_id),
            team_id=str(team_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("remove_team_from_meet_error", meet_id=str(meet_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove team from meet: {e}",
        ) from e
