"""Team API endpoints.

All endpoints require authentication (invite-only app).
Create, Update, Delete require admin role.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from swimcuttimes import get_logger
from swimcuttimes.api.auth import AdminUser, CurrentUser
from swimcuttimes.api.dependencies import TeamDAODep
from swimcuttimes.models import Team, TeamType

logger = get_logger(__name__)

router = APIRouter(prefix="/teams", tags=["teams"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================


class TeamCreate(BaseModel):
    """Request body for creating a team."""

    name: str
    team_type: TeamType
    sanctioning_body: str
    lsc: str | None = None
    division: str | None = None
    state: str | None = None
    country: str | None = None


class TeamUpdate(BaseModel):
    """Request body for updating a team (partial)."""

    name: str | None = None
    team_type: TeamType | None = None
    sanctioning_body: str | None = None
    lsc: str | None = None
    division: str | None = None
    state: str | None = None
    country: str | None = None


# =============================================================================
# VALIDATION HELPERS
# =============================================================================


def validate_team_type_fields(
    team_type: TeamType,
    lsc: str | None,
    division: str | None,
    state: str | None,
    country: str | None,
) -> None:
    """Validate required fields based on team type."""
    if team_type == TeamType.CLUB and not lsc:
        raise ValueError("LSC code is required for club teams")
    elif team_type == TeamType.COLLEGE and not division:
        raise ValueError("Division is required for college teams")
    elif team_type == TeamType.HIGH_SCHOOL and not state:
        raise ValueError("State is required for high school teams")
    elif team_type in (TeamType.NATIONAL, TeamType.OLYMPIC) and not country:
        raise ValueError("Country is required for national/olympic teams")


# =============================================================================
# CREATE (Admin only)
# =============================================================================


@router.post("", response_model=Team, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    user: AdminUser,
    dao: TeamDAODep,
) -> Team:
    """Create a new team (admin only)."""
    try:
        validate_team_type_fields(
            data.team_type,
            data.lsc,
            data.division,
            data.state,
            data.country,
        )

        team = Team(
            name=data.name,
            team_type=data.team_type,
            sanctioning_body=data.sanctioning_body,
            lsc=data.lsc,
            division=data.division,
            state=data.state,
            country=data.country,
        )
        result = dao.create(team)

        logger.info(
            "team_created",
            team_id=str(result.id),
            team_name=data.name,
            team_type=data.team_type.value,
        )
        return result

    except ValueError as e:
        logger.warning("team_create_validation_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        error_str = str(e).lower()
        if "duplicate" in error_str or "unique" in error_str:
            logger.warning("team_create_duplicate", team_name=data.name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A team named '{data.name}' already exists",
            ) from e
        logger.error("team_create_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team: {e}",
        ) from e


# =============================================================================
# READ - List (Authenticated users)
# =============================================================================


@router.get("", response_model=list[Team])
def list_teams(
    user: CurrentUser,
    dao: TeamDAODep,
    name: str | None = Query(None, description="Partial name match"),
    team_type: TeamType | None = None,
    sanctioning_body: str | None = Query(None, description="e.g., 'USA Swimming', 'NCAA D1'"),
    lsc: str | None = Query(None, description="LSC code for club teams"),
    division: str | None = Query(None, description="Division for college teams"),
    state: str | None = Query(None, description="State abbreviation"),
    country: str | None = Query(None, description="Country code"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[Team]:
    """Search teams with optional filters."""
    return dao.search(
        name=name,
        team_type=team_type,
        sanctioning_body=sanctioning_body,
        lsc=lsc,
        division=division,
        state=state,
        country=country,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# READ - Get by ID (Authenticated users)
# =============================================================================


@router.get("/{team_id}", response_model=Team)
def get_team(
    team_id: UUID,
    user: CurrentUser,
    dao: TeamDAODep,
) -> Team:
    """Get a specific team by ID."""
    result = dao.get_by_id(team_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return result


# =============================================================================
# UPDATE (Admin only)
# =============================================================================


@router.patch("/{team_id}", response_model=Team)
def update_team(
    team_id: UUID,
    data: TeamUpdate,
    user: AdminUser,
    dao: TeamDAODep,
) -> Team:
    """Update a team (admin only). Partial update - only provided fields are changed."""
    # First, get existing team
    existing = dao.get_by_id(team_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    try:
        # Determine final values for validation
        final_team_type = data.team_type if data.team_type is not None else existing.team_type
        final_lsc = data.lsc if data.lsc is not None else existing.lsc
        final_division = data.division if data.division is not None else existing.division
        final_state = data.state if data.state is not None else existing.state
        final_country = data.country if data.country is not None else existing.country

        # Validate the final state
        validate_team_type_fields(
            final_team_type,
            final_lsc,
            final_division,
            final_state,
            final_country,
        )

        # Build update dict
        updates = data.model_dump(exclude_unset=True)

        result = dao.partial_update(team_id, updates)

        logger.info(
            "team_updated",
            team_id=str(team_id),
            updated_fields=list(updates.keys()),
        )
        return result

    except ValueError as e:
        logger.warning("team_update_validation_failed", team_id=str(team_id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e).lower()
        if "duplicate" in error_str or "unique" in error_str:
            logger.warning("team_update_duplicate", team_id=str(team_id), new_name=data.name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A team named '{data.name}' already exists",
            ) from e
        logger.error("team_update_error", team_id=str(team_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update team: {e}",
        ) from e


# =============================================================================
# DELETE (Admin only)
# =============================================================================


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: UUID,
    user: AdminUser,
    dao: TeamDAODep,
) -> None:
    """Delete a team (admin only)."""
    existing = dao.get_by_id(team_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    try:
        deleted = dao.delete(team_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

        logger.info(
            "team_deleted",
            team_id=str(team_id),
            team_name=existing.name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("team_delete_error", team_id=str(team_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team: {e}",
        ) from e
