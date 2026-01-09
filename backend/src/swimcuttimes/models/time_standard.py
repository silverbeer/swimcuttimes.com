"""Time standard models for qualifying times."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, computed_field

from swimcuttimes.models.event import Event
from swimcuttimes.models.swimmer import Gender


class TimeStandard(BaseModel):
    """A qualifying time standard (cut time).

    Examples:
    - NE Swimming Silver Championship 15-18 Girls 100 Free SCY: 56.29
    - USA Swimming Futures 100 Free LCM: 57.59
    - NCAA D1 Qualifying 200 IM SCY: 1:44.59
    """

    id: UUID | None = None

    # Event identification
    event: Event
    gender: Gender

    # Age group (None or "Open" = no age restriction)
    age_group: str | None = None

    # Standard identification
    standard_name: str  # e.g., "Silver Championship", "Futures", "NCAA D1"
    cut_level: str  # e.g., "Cut Time", "Cut Off Time", "A", "AA"
    sanctioning_body: str  # e.g., "NE Swimming", "USA Swimming", "NCAA D1"

    # The time (stored as centiseconds for precision)
    time_centiseconds: int

    # Qualifying period
    qualifying_start: date | None = None
    qualifying_end: date | None = None
    effective_year: int

    @computed_field
    @property
    def time_formatted(self) -> str:
        """Format time as MM:SS.cc or SS.cc."""
        total_seconds = self.time_centiseconds / 100
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60

        if minutes > 0:
            return f"{minutes}:{seconds:05.2f}"
        return f"{seconds:.2f}"

    @property
    def is_open(self) -> bool:
        """Check if this standard has no age restriction."""
        return self.age_group is None or self.age_group.lower() == "open"

    def __str__(self) -> str:
        age_str = f" {self.age_group}" if self.age_group and not self.is_open else ""
        return (
            f"{self.standard_name}{age_str} {self.gender.value} "
            f"{self.event.short_name}: {self.time_formatted}"
        )


def parse_time_to_centiseconds(time_str: str) -> int:
    """Parse a time string (MM:SS.cc or SS.cc) to centiseconds.

    Examples:
        "56.29" -> 5629
        "1:05.79" -> 6579
        "10:29.99" -> 62999
    """
    time_str = time_str.strip()

    if ":" in time_str:
        parts = time_str.split(":")
        minutes = int(parts[0])
        seconds = float(parts[1])
        total_seconds = minutes * 60 + seconds
    else:
        total_seconds = float(time_str)

    return int(round(total_seconds * 100))


def format_centiseconds_to_time(centiseconds: int) -> str:
    """Format centiseconds to a time string (MM:SS.cc or SS.cc)."""
    total_seconds = centiseconds / 100
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    if minutes > 0:
        return f"{minutes}:{seconds:05.2f}"
    return f"{seconds:.2f}"
