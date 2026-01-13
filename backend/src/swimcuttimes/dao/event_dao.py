"""Data Access Object for Events."""

from supabase import Client
from swimcuttimes.dao.base import BaseDAO
from swimcuttimes.models.event import Course, Event, Stroke


class EventDAO(BaseDAO[Event]):
    """DAO for Event entities."""

    table_name = "events"
    model_class = Event

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_stroke_distance_course(
        self, stroke: Stroke, distance: int, course: Course
    ) -> Event | None:
        """Find an event by its unique combination of stroke, distance, and course.

        Args:
            stroke: The swimming stroke
            distance: The distance in yards/meters
            course: The course type (SCY, SCM, LCM)

        Returns:
            The Event or None if not found
        """
        result = (
            self.table.select("*")
            .eq("stroke", stroke.value)
            .eq("distance", distance)
            .eq("course", course.value)
            .execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def find_or_create(self, stroke: Stroke, distance: int, course: Course) -> Event:
        """Find an event or create it if it doesn't exist.

        Args:
            stroke: The swimming stroke
            distance: The distance in yards/meters
            course: The course type (SCY, SCM, LCM)

        Returns:
            The existing or newly created Event
        """
        existing = self.find_by_stroke_distance_course(stroke, distance, course)
        if existing:
            return existing

        event = Event(stroke=stroke, distance=distance, course=course)
        return self.create(event)

    def find_by_stroke(self, stroke: Stroke) -> list[Event]:
        """Find all events for a given stroke.

        Args:
            stroke: The swimming stroke

        Returns:
            List of Events for that stroke
        """
        result = self.table.select("*").eq("stroke", stroke.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_course(self, course: Course) -> list[Event]:
        """Find all events for a given course.

        Args:
            course: The course type (SCY, SCM, LCM)

        Returns:
            List of Events for that course
        """
        result = self.table.select("*").eq("course", course.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_distance(self, distance: int) -> list[Event]:
        """Find all events for a given distance.

        Args:
            distance: The distance in yards/meters

        Returns:
            List of Events for that distance
        """
        result = self.table.select("*").eq("distance", distance).execute()
        return [self._to_model(row) for row in result.data]

    def get_event_id(self, stroke: Stroke, distance: int, course: Course) -> str | None:
        """Get just the ID for an event.

        Args:
            stroke: The swimming stroke
            distance: The distance in yards/meters
            course: The course type (SCY, SCM, LCM)

        Returns:
            The event's ID (short ID string) or None if not found
        """
        result = (
            self.table.select("id")
            .eq("stroke", stroke.value)
            .eq("distance", distance)
            .eq("course", course.value)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]["id"]

    def _to_model(self, row: dict) -> Event:
        """Convert database row to Event model."""
        return Event(
            id=row["id"] if row.get("id") else None,
            stroke=Stroke(row["stroke"]),
            distance=row["distance"],
            course=Course(row["course"]),
        )

    def _to_db(self, model: Event) -> dict:
        """Convert Event model to database row."""
        data = {
            "stroke": model.stroke.value,
            "distance": model.distance,
            "course": model.course.value,
        }
        if model.id:
            data["id"] = str(model.id)
        return data
