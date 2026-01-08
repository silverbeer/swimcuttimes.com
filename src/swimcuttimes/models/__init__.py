"""Pydantic models for swim cut times tracking."""

from swimcuttimes.models.event import (
    METERS_TO_SCY_DISTANCE,
    SCY_TO_METERS_DISTANCE,
    VALID_DISTANCES,
    Course,
    Event,
    Stroke,
)
from swimcuttimes.models.meet import Meet, MeetType
from swimcuttimes.models.swim_time import Round, Split, SwimTime
from swimcuttimes.models.swimmer import Gender, Swimmer
from swimcuttimes.models.team import SwimmerTeam, Team, TeamType
from swimcuttimes.models.time_standard import (
    TimeStandard,
    format_centiseconds_to_time,
    parse_time_to_centiseconds,
)

__all__ = [
    # Event
    "Course",
    "Event",
    "METERS_TO_SCY_DISTANCE",
    "SCY_TO_METERS_DISTANCE",
    "Stroke",
    "VALID_DISTANCES",
    # Meet
    "Meet",
    "MeetType",
    # Swim Time
    "Round",
    "Split",
    "SwimTime",
    # Swimmer
    "Gender",
    "Swimmer",
    # Team
    "SwimmerTeam",
    "Team",
    "TeamType",
    # Time Standard
    "TimeStandard",
    "format_centiseconds_to_time",
    "parse_time_to_centiseconds",
]
