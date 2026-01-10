"""Meet model for swim competitions."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, field_validator

from swimcuttimes.models.event import Course


class MeetType(StrEnum):
    """Types of swim meets."""

    CHAMPIONSHIP = "championship"  # Championship meet (LSC, Sectionals, Nationals)
    INVITATIONAL = "invitational"  # Invitational meet
    DUAL = "dual"  # Dual meet between two teams
    TIME_TRIAL = "time_trial"  # Time trial event


class Meet(BaseModel):
    """A swim meet/competition."""

    id: UUID | None = None
    name: str
    location: str  # Venue name
    city: str
    state: str | None = None
    country: str = "USA"

    start_date: date
    end_date: date | None = None  # Single-day meets have None

    course: Course
    lanes: int  # Number of lanes (6, 8, 10)
    indoor: bool = True  # True = indoor, False = outdoor

    sanctioning_body: str  # e.g., "NE Swimming", "USA Swimming", "NCAA"
    meet_type: MeetType

    @field_validator("lanes")
    @classmethod
    def validate_lanes(cls, v: int) -> int:
        if v not in (6, 8, 10):
            raise ValueError("Lanes must be 6, 8, or 10")
        return v

    def __str__(self) -> str:
        return self.name


class MeetTeam(BaseModel):
    """Association between a meet and a participating team.

    Tracks which teams participate in a meet. A team can be marked
    as host for home meets.
    """

    id: UUID | None = None
    meet_id: UUID
    team_id: UUID
    is_host: bool = False
