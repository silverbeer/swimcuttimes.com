"""Event models and enums for swimming events."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, model_validator


class Stroke(StrEnum):
    """Swimming strokes."""

    FREESTYLE = "freestyle"
    BACKSTROKE = "backstroke"
    BREASTSTROKE = "breaststroke"
    BUTTERFLY = "butterfly"
    IM = "im"  # Individual Medley


class Course(StrEnum):
    """Pool course types."""

    SCY = "scy"  # Short Course Yards (25 yards)
    SCM = "scm"  # Short Course Meters (25 meters)
    LCM = "lcm"  # Long Course Meters (50 meters)


# Standard competitive distances
VALID_DISTANCES = {25, 50, 100, 200, 400, 500, 800, 1000, 1500, 1650}

# Event equivalents across courses (SCY <-> meters)
# Maps (distance, course) -> equivalent distance in the other system
SCY_TO_METERS_DISTANCE: dict[int, int] = {
    500: 400,
    1000: 800,
    1650: 1500,
}

METERS_TO_SCY_DISTANCE: dict[int, int] = {
    400: 500,
    800: 1000,
    1500: 1650,
}

# Course-specific distances for validation
SCY_ONLY_DISTANCES = {500, 1000, 1650}  # Yards only
METERS_ONLY_DISTANCES = {400, 800, 1500}  # Meters only (SCM/LCM)


class Event(BaseModel):
    """A swimming event (e.g., 100 Freestyle SCY)."""

    id: UUID | None = None
    stroke: Stroke
    distance: int
    course: Course

    @model_validator(mode="after")
    def validate_distance_course(self) -> "Event":
        """Validate that distance is valid for the course type.

        Note: Distance equivalents (500y/400m, 1000y/800m, 1650y/1500m) only apply
        to freestyle events. IM events use the same distances across all courses
        (e.g., 400 IM exists in SCY, SCM, and LCM).
        """
        # Only validate distance equivalents for freestyle
        if self.stroke != Stroke.FREESTYLE:
            return self

        if self.course == Course.SCY and self.distance in METERS_ONLY_DISTANCES:
            raise ValueError(
                f"{self.distance} is a meters distance, not valid for SCY freestyle. "
                f"SCY equivalent: {METERS_TO_SCY_DISTANCE[self.distance]}"
            )
        if self.course in (Course.SCM, Course.LCM) and self.distance in SCY_ONLY_DISTANCES:
            raise ValueError(
                f"{self.distance} is a yards distance, not valid for {self.course.value.upper()} freestyle. "
                f"Meters equivalent: {SCY_TO_METERS_DISTANCE[self.distance]}"
            )
        return self

    def __str__(self) -> str:
        return f"{self.distance} {self.stroke.value.title()} {self.course.value.upper()}"

    @property
    def short_name(self) -> str:
        """Short name for display (e.g., '100 Free')."""
        stroke_short = {
            Stroke.FREESTYLE: "Free",
            Stroke.BACKSTROKE: "Back",
            Stroke.BREASTSTROKE: "Breast",
            Stroke.BUTTERFLY: "Fly",
            Stroke.IM: "IM",
        }
        return f"{self.distance} {stroke_short[self.stroke]}"

    def get_equivalent(self, target_course: Course) -> "Event":
        """Get the equivalent event in another course.

        For distance events with course-specific distances (500y/400m, etc.),
        returns the appropriate equivalent. For other events, same distance.
        """
        if self.course == target_course:
            return self

        # Converting from SCY to meters
        if self.course == Course.SCY and target_course in (Course.SCM, Course.LCM):
            equiv_distance = SCY_TO_METERS_DISTANCE.get(self.distance, self.distance)
            return Event(stroke=self.stroke, distance=equiv_distance, course=target_course)

        # Converting from meters to SCY
        if self.course in (Course.SCM, Course.LCM) and target_course == Course.SCY:
            equiv_distance = METERS_TO_SCY_DISTANCE.get(self.distance, self.distance)
            return Event(stroke=self.stroke, distance=equiv_distance, course=target_course)

        # Converting between SCM and LCM (same distances)
        return Event(stroke=self.stroke, distance=self.distance, course=target_course)
