"""Team models for swimming organizations."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class TeamType(StrEnum):
    """Types of swimming teams/organizations."""

    CLUB = "club"  # Year-round swim club
    HIGH_SCHOOL = "high_school"  # High school team
    COLLEGE = "college"  # College/university team
    NATIONAL = "national"  # National team
    OLYMPIC = "olympic"  # Olympic team


class Team(BaseModel):
    """A swimming team or organization."""

    id: str | None = None
    name: str
    team_type: TeamType
    sanctioning_body: str  # e.g., "USA Swimming", "NCAA D1", "FINA"

    # Type-specific fields (nullable based on team_type)
    lsc: str | None = None  # LSC code for club teams (e.g., "NE", "PV")
    division: str | None = None  # For college teams (e.g., "D1", "D2", "D3", "NAIA")
    state: str | None = None  # State for high school teams
    country: str | None = None  # Country code for national/olympic teams

    def __str__(self) -> str:
        return self.name


class SwimmerTeam(BaseModel):
    """Association between a swimmer and a team with temporal data.

    Supports:
    - Multiple concurrent team memberships (club + high school)
    - Historical tracking of team changes
    """

    id: str | None = None
    swimmer_id: str
    team_id: str
    start_date: date
    end_date: date | None = None  # None = current membership

    @property
    def is_current(self) -> bool:
        """Check if this is a current team membership."""
        return self.end_date is None or self.end_date >= date.today()
