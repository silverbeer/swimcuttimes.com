"""Swimmer API endpoints.

All endpoints require authentication (invite-only app).
Create, Update require admin or coach role.
Delete requires admin role.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminOrCoachUser, AdminUser, CurrentUser
from swimcuttimes.api.dependencies import SwimmerDAODep, SwimmerTeamDAODep, TeamDAODep
from swimcuttimes.models import Gender, Swimmer, SwimmerTeam

logger = get_logger(__name__)

router = APIRouter(prefix="/swimmers", tags=["swimmers"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================


class SwimmerCreate(BaseModel):
    """Request body for creating a swimmer."""

    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    user_id: UUID | None = None
    usa_swimming_id: str | None = None
    swimcloud_url: str | None = None


class SwimmerUpdate(BaseModel):
    """Request body for updating a swimmer (partial)."""

    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    user_id: UUID | None = None
    usa_swimming_id: str | None = None
    swimcloud_url: str | None = None


class SwimmerResponse(BaseModel):
    """Response model for swimmer with computed fields."""

    id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    user_id: UUID | None
    usa_swimming_id: str | None
    swimcloud_url: str | None
    age: int
    age_group: str

    @classmethod
    def from_swimmer(cls, swimmer: Swimmer) -> "SwimmerResponse":
        """Create response from Swimmer model."""
        return cls(
            id=swimmer.id,
            first_name=swimmer.first_name,
            last_name=swimmer.last_name,
            date_of_birth=swimmer.date_of_birth,
            gender=swimmer.gender,
            user_id=swimmer.user_id,
            usa_swimming_id=swimmer.usa_swimming_id,
            swimcloud_url=swimmer.swimcloud_url,
            age=swimmer.age,
            age_group=swimmer.age_group_on_date(date.today()),
        )


class TeamAssignment(BaseModel):
    """Request to assign swimmer to team."""

    team_id: UUID
    start_date: date = Field(default_factory=date.today)


class SwimmerTeamResponse(BaseModel):
    """Response for swimmer-team association."""

    id: UUID
    swimmer_id: UUID
    team_id: UUID
    team_name: str
    start_date: date
    end_date: date | None
    is_current: bool


# =============================================================================
# CREATE (Admin or Coach)
# =============================================================================


@router.post("", response_model=SwimmerResponse, status_code=status.HTTP_201_CREATED)
def create_swimmer(
    data: SwimmerCreate,
    user: AdminOrCoachUser,
    dao: SwimmerDAODep,
) -> SwimmerResponse:
    """Create a new swimmer (admin or coach only)."""
    try:
        # Check for duplicate USA Swimming ID
        if data.usa_swimming_id:
            existing = dao.find_by_usa_swimming_id(data.usa_swimming_id)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A swimmer with USA Swimming ID '{data.usa_swimming_id}' already exists",
                )

        swimmer = Swimmer(
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            user_id=data.user_id,
            usa_swimming_id=data.usa_swimming_id,
            swimcloud_url=data.swimcloud_url,
        )
        result = dao.create(swimmer)

        logger.info(
            "swimmer_created",
            swimmer_id=str(result.id),
            swimmer_name=f"{data.first_name} {data.last_name}",
        )
        return SwimmerResponse.from_swimmer(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swimmer_create_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create swimmer: {e}",
        ) from e


# =============================================================================
# READ - List (Authenticated users)
# =============================================================================


@router.get("", response_model=list[SwimmerResponse])
def list_swimmers(
    user: CurrentUser,
    dao: SwimmerDAODep,
    name: str | None = Query(None, description="Search in first or last name"),
    gender: Gender | None = Query(None, description="Filter by gender"),
    min_age: int | None = Query(None, description="Minimum age"),
    max_age: int | None = Query(None, description="Maximum age"),
    limit: int = Query(100, ge=1, le=500),
) -> list[SwimmerResponse]:
    """Search swimmers with optional filters."""
    swimmers = dao.search(
        name=name,
        gender=gender,
        min_age=min_age,
        max_age=max_age,
        limit=limit,
    )
    return [SwimmerResponse.from_swimmer(s) for s in swimmers]


# =============================================================================
# READ - Get by ID (Authenticated users)
# =============================================================================


@router.get("/{swimmer_id}", response_model=SwimmerResponse)
def get_swimmer(
    swimmer_id: UUID,
    user: CurrentUser,
    dao: SwimmerDAODep,
) -> SwimmerResponse:
    """Get a specific swimmer by ID."""
    result = dao.get_by_id(swimmer_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")
    return SwimmerResponse.from_swimmer(result)


# =============================================================================
# UPDATE (Admin or Coach)
# =============================================================================


@router.patch("/{swimmer_id}", response_model=SwimmerResponse)
def update_swimmer(
    swimmer_id: UUID,
    data: SwimmerUpdate,
    user: AdminOrCoachUser,
    dao: SwimmerDAODep,
) -> SwimmerResponse:
    """Update a swimmer (admin or coach only). Partial update - only provided fields are changed."""
    # First, get existing swimmer
    existing = dao.get_by_id(swimmer_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    try:
        # Check for duplicate USA Swimming ID if being changed
        if data.usa_swimming_id and data.usa_swimming_id != existing.usa_swimming_id:
            other = dao.find_by_usa_swimming_id(data.usa_swimming_id)
            if other and other.id != swimmer_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A swimmer with USA Swimming ID '{data.usa_swimming_id}' already exists",
                )

        # Build update dict
        updates = data.model_dump(exclude_unset=True)

        result = dao.partial_update(swimmer_id, updates)

        logger.info(
            "swimmer_updated",
            swimmer_id=str(swimmer_id),
            updated_fields=list(updates.keys()),
        )
        return SwimmerResponse.from_swimmer(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swimmer_update_error", swimmer_id=str(swimmer_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update swimmer: {e}",
        ) from e


# =============================================================================
# DELETE (Admin only)
# =============================================================================


@router.delete("/{swimmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_swimmer(
    swimmer_id: UUID,
    user: AdminUser,
    dao: SwimmerDAODep,
) -> None:
    """Delete a swimmer (admin only)."""
    existing = dao.get_by_id(swimmer_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    try:
        deleted = dao.delete(swimmer_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

        logger.info(
            "swimmer_deleted",
            swimmer_id=str(swimmer_id),
            swimmer_name=f"{existing.first_name} {existing.last_name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("swimmer_delete_error", swimmer_id=str(swimmer_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete swimmer: {e}",
        ) from e


# =============================================================================
# TEAM ASSIGNMENTS
# =============================================================================


@router.post(
    "/{swimmer_id}/teams",
    response_model=SwimmerTeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_swimmer_to_team(
    swimmer_id: UUID,
    data: TeamAssignment,
    user: AdminOrCoachUser,
    swimmer_dao: SwimmerDAODep,
    team_dao: TeamDAODep,
    swimmer_team_dao: SwimmerTeamDAODep,
) -> SwimmerTeamResponse:
    """Assign a swimmer to a team (admin or coach only)."""
    # Verify swimmer exists
    swimmer = swimmer_dao.get_by_id(swimmer_id)
    if not swimmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    # Verify team exists
    team = team_dao.get_by_id(data.team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    try:
        # Check for existing active membership on this team
        existing = swimmer_team_dao.find_by_swimmer_and_team(swimmer_id, data.team_id)
        active = [st for st in existing if st.is_current]
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Swimmer is already a current member of '{team.name}'",
            )

        # Create assignment
        assignment = SwimmerTeam(
            swimmer_id=swimmer_id,
            team_id=data.team_id,
            start_date=data.start_date,
        )
        result = swimmer_team_dao.create(assignment)

        logger.info(
            "swimmer_assigned_to_team",
            swimmer_id=str(swimmer_id),
            team_id=str(data.team_id),
            team_name=team.name,
        )

        return SwimmerTeamResponse(
            id=result.id,
            swimmer_id=result.swimmer_id,
            team_id=result.team_id,
            team_name=team.name,
            start_date=result.start_date,
            end_date=result.end_date,
            is_current=result.is_current,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "swimmer_team_assign_error",
            swimmer_id=str(swimmer_id),
            team_id=str(data.team_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign swimmer to team: {e}",
        ) from e


@router.get("/{swimmer_id}/teams", response_model=list[SwimmerTeamResponse])
def list_swimmer_teams(
    swimmer_id: UUID,
    user: CurrentUser,
    swimmer_dao: SwimmerDAODep,
    team_dao: TeamDAODep,
    swimmer_team_dao: SwimmerTeamDAODep,
    current_only: bool = Query(True, description="Only show current team memberships"),
) -> list[SwimmerTeamResponse]:
    """List teams a swimmer belongs to."""
    # Verify swimmer exists
    swimmer = swimmer_dao.get_by_id(swimmer_id)
    if not swimmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    if current_only:
        assignments = swimmer_team_dao.find_current_by_swimmer(swimmer_id)
    else:
        assignments = swimmer_team_dao.find_by_swimmer(swimmer_id)

    # Fetch team names
    responses = []
    for assignment in assignments:
        team = team_dao.get_by_id(assignment.team_id)
        team_name = team.name if team else "Unknown"
        responses.append(
            SwimmerTeamResponse(
                id=assignment.id,
                swimmer_id=assignment.swimmer_id,
                team_id=assignment.team_id,
                team_name=team_name,
                start_date=assignment.start_date,
                end_date=assignment.end_date,
                is_current=assignment.is_current,
            )
        )

    return responses


@router.delete("/{swimmer_id}/teams/{team_id}", status_code=status.HTTP_200_OK)
def end_swimmer_team_membership(
    swimmer_id: UUID,
    team_id: UUID,
    user: AdminOrCoachUser,
    swimmer_dao: SwimmerDAODep,
    team_dao: TeamDAODep,
    swimmer_team_dao: SwimmerTeamDAODep,
    end_date: date = Query(default_factory=date.today, description="Membership end date"),
) -> SwimmerTeamResponse:
    """End a swimmer's current team membership (admin or coach only)."""
    # Verify swimmer exists
    swimmer = swimmer_dao.get_by_id(swimmer_id)
    if not swimmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swimmer not found")

    # Verify team exists
    team = team_dao.get_by_id(team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Find current membership
    existing = swimmer_team_dao.find_by_swimmer_and_team(swimmer_id, team_id)
    current = [st for st in existing if st.is_current]

    if not current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swimmer is not a current member of '{team.name}'",
        )

    try:
        membership = current[0]
        result = swimmer_team_dao.end_membership(membership.id, end_date)

        logger.info(
            "swimmer_team_membership_ended",
            swimmer_id=str(swimmer_id),
            team_id=str(team_id),
            team_name=team.name,
            end_date=end_date.isoformat(),
        )

        return SwimmerTeamResponse(
            id=result.id,
            swimmer_id=result.swimmer_id,
            team_id=result.team_id,
            team_name=team.name,
            start_date=result.start_date,
            end_date=result.end_date,
            is_current=result.is_current,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "swimmer_team_end_error",
            swimmer_id=str(swimmer_id),
            team_id=str(team_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end team membership: {e}",
        ) from e
