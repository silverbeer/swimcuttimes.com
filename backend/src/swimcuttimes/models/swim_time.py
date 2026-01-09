"""Swim time model for recorded race times."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, computed_field, field_validator

from swimcuttimes.models.time_standard import format_centiseconds_to_time


class Split(BaseModel):
    """A split time recorded during a race.

    Stores cumulative time at a given distance. Interval times
    can be calculated from consecutive splits.

    Example for 200 Free:
        Split(distance=50, time_centiseconds=2827)   # 28.27 at 50m
        Split(distance=100, time_centiseconds=5844)  # 58.44 at 100m
        Split(distance=150, time_centiseconds=8919)  # 1:29.19 at 150m
    """

    id: UUID | None = None
    swim_time_id: UUID | None = None  # Foreign key to SwimTime

    distance: int  # Cumulative distance (50, 100, 150, etc.)
    time_centiseconds: int  # Cumulative time at this distance

    @computed_field
    @property
    def time_formatted(self) -> str:
        """Format cumulative time as MM:SS.cc or SS.cc."""
        return format_centiseconds_to_time(self.time_centiseconds)


class Round(StrEnum):
    """Round of competition."""

    PRELIMS = "prelims"
    FINALS = "finals"
    CONSOLATION = "consolation"  # Consolation finals (typically places 9-16)
    BONUS_FINALS = "bonus_finals"  # Bonus finals (typically places 17-24)
    TIME_TRIAL = "time_trial"


class SwimTime(BaseModel):
    """A swimmer's recorded time for an event.

    Represents a single swim at a specific meet, tracking all relevant
    details including round, lane, and result.
    """

    id: UUID | None = None

    # Required references
    swimmer_id: UUID
    event_id: UUID
    meet_id: UUID

    # The time (stored as centiseconds for precision)
    time_centiseconds: int

    # When and where
    swim_date: date
    team_id: UUID  # Team swimmer represented at time of swim

    # Competition details (optional)
    round: Round | None = None
    lane: int | None = None  # Lane number 1-10
    place: int | None = None  # Finish place in heat/final

    # Status
    official: bool = True  # Official or exhibition/unofficial
    dq: bool = False  # Disqualified
    dq_reason: str | None = None

    # Splits (loaded separately, not always present)
    splits: list[Split] = []

    @field_validator("lane")
    @classmethod
    def validate_lane(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Lane must be between 1 and 10")
        return v

    @computed_field
    @property
    def time_formatted(self) -> str:
        """Format time as MM:SS.cc or SS.cc."""
        return format_centiseconds_to_time(self.time_centiseconds)

    @property
    def is_valid(self) -> bool:
        """Check if this is a valid, countable time."""
        return self.official and not self.dq

    def compare_to_standard(self, standard_centiseconds: int) -> float:
        """Compare this time to a standard.

        Returns:
            Difference in seconds (negative = faster than standard)
        """
        return (self.time_centiseconds - standard_centiseconds) / 100

    def meets_standard(self, standard_centiseconds: int) -> bool:
        """Check if this time meets or beats a standard."""
        return self.is_valid and self.time_centiseconds <= standard_centiseconds

    def get_split(self, distance: int) -> Split | None:
        """Get the split at a specific distance.

        Args:
            distance: Cumulative distance (50, 100, 150, etc.)

        Returns:
            Split at that distance or None if not recorded
        """
        for split in self.splits:
            if split.distance == distance:
                return split
        return None

    def get_split_time(self, distance: int) -> int | None:
        """Get cumulative time in centiseconds at a specific distance.

        Args:
            distance: Cumulative distance (50, 100, 150, etc.)

        Returns:
            Cumulative time in centiseconds or None if not recorded
        """
        split = self.get_split(distance)
        return split.time_centiseconds if split else None

    def get_interval(self, distance: int) -> int | None:
        """Get interval time for a specific segment.

        Args:
            distance: End distance of the segment (100 = time for 50-100 segment)

        Returns:
            Interval time in centiseconds or None if splits not available

        Example:
            For a 200 Free with splits at 50, 100, 150:
            get_interval(50) -> time for 0-50 (first split)
            get_interval(100) -> time for 50-100 (second split minus first)
            get_interval(150) -> time for 100-150 (third minus second)
        """
        current = self.get_split(distance)
        if not current:
            return None

        # Find previous split distance
        sorted_splits = sorted(self.splits, key=lambda s: s.distance)
        prev_time = 0
        for split in sorted_splits:
            if split.distance == distance:
                return split.time_centiseconds - prev_time
            prev_time = split.time_centiseconds

        return None

    def split_meets_standard(self, distance: int, standard_centiseconds: int) -> bool:
        """Check if a split meets or beats a standard.

        Useful for checking if a 50-split qualifies for 50 Free cut time.

        Args:
            distance: Split distance to check
            standard_centiseconds: Cut time to compare against

        Returns:
            True if split beats the standard
        """
        split_time = self.get_split_time(distance)
        if split_time is None:
            return False
        return self.is_valid and split_time <= standard_centiseconds
