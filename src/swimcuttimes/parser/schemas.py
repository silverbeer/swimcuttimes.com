"""Schemas for parsed time standard data from images."""

from pydantic import BaseModel

from swimcuttimes.models.event import Course, Stroke
from swimcuttimes.models.swimmer import Gender


class ParsedTimeEntry(BaseModel):
    """A single parsed time entry from an image."""

    event_distance: int
    event_stroke: Stroke
    course: Course
    gender: Gender
    time_str: str  # Original time string (e.g., "56.29", "1:05.79")
    cut_level: str  # e.g., "Cut Time", "Cut Off Time"


class ParsedTimeStandardSheet(BaseModel):
    """Complete parsed result from a time standard image.

    Captures all metadata and individual time entries from a
    time standard sheet (like NE Silver Championship).
    """

    # Metadata from the image
    title: str  # e.g., "2025 New England Swimming Silver Championship Qualifying Times"
    sanctioning_body: str  # e.g., "NE Swimming"
    standard_name: str  # e.g., "Silver Championship"
    effective_year: int  # e.g., 2025
    age_group: str | None = None  # e.g., "15-18" or None for Open
    qualifying_period_start: str | None = None  # e.g., "January 1, 2024"
    qualifying_period_end: str | None = None  # e.g., "Meet Entry Date"

    # All parsed time entries
    entries: list[ParsedTimeEntry]

    @property
    def entry_count(self) -> int:
        """Number of time entries parsed."""
        return len(self.entries)

    def entries_by_gender(self, gender: Gender) -> list[ParsedTimeEntry]:
        """Filter entries by gender."""
        return [e for e in self.entries if e.gender == gender]

    def entries_by_course(self, course: Course) -> list[ParsedTimeEntry]:
        """Filter entries by course."""
        return [e for e in self.entries if e.course == course]
