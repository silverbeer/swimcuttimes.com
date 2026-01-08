"""Data Access Object for Time Standards."""

from datetime import date
from uuid import UUID

from supabase import Client
from swimcuttimes.dao.base import BaseDAO
from swimcuttimes.dao.event_dao import EventDAO
from swimcuttimes.models.event import Course, Event, Stroke
from swimcuttimes.models.swimmer import Gender
from swimcuttimes.models.time_standard import TimeStandard


class TimeStandardDAO(BaseDAO[TimeStandard]):
    """DAO for TimeStandard entities."""

    table_name = "time_standards"
    model_class = TimeStandard

    def __init__(self, client: Client | None = None):
        super().__init__(client)
        self.event_dao = EventDAO(self.client)

    def find_by_event(self, event_id: UUID) -> list[TimeStandard]:
        """Find all time standards for a specific event.

        Args:
            event_id: The event's UUID

        Returns:
            List of TimeStandards for that event
        """
        result = (
            self.table.select("*, events(*)")
            .eq("event_id", str(event_id))
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_event_and_gender(
        self, event_id: UUID, gender: Gender
    ) -> list[TimeStandard]:
        """Find time standards for a specific event and gender.

        Args:
            event_id: The event's UUID
            gender: The gender (M or F)

        Returns:
            List of TimeStandards matching criteria
        """
        result = (
            self.table.select("*, events(*)")
            .eq("event_id", str(event_id))
            .eq("gender", gender.value)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_sanctioning_body(self, sanctioning_body: str) -> list[TimeStandard]:
        """Find all time standards from a specific sanctioning body.

        Args:
            sanctioning_body: e.g., "NE Swimming", "USA Swimming"

        Returns:
            List of TimeStandards from that body
        """
        result = (
            self.table.select("*, events(*)")
            .eq("sanctioning_body", sanctioning_body)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_standard_name(self, standard_name: str) -> list[TimeStandard]:
        """Find all time standards with a specific name.

        Args:
            standard_name: e.g., "Silver Championship", "Futures"

        Returns:
            List of TimeStandards with that name
        """
        result = (
            self.table.select("*, events(*)")
            .eq("standard_name", standard_name)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_age_group(self, age_group: str | None) -> list[TimeStandard]:
        """Find all time standards for a specific age group.

        Args:
            age_group: e.g., "15-18", "Open", or None for no restriction

        Returns:
            List of TimeStandards for that age group
        """
        query = self.table.select("*, events(*)")

        if age_group is None:
            query = query.is_("age_group", "null")
        else:
            query = query.eq("age_group", age_group)

        result = query.execute()
        return [self._to_model(row) for row in result.data]

    def find_by_year(self, year: int) -> list[TimeStandard]:
        """Find all time standards for a specific effective year.

        Args:
            year: The effective year

        Returns:
            List of TimeStandards for that year
        """
        result = (
            self.table.select("*, events(*)")
            .eq("effective_year", year)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_standards_for_swimmer(
        self,
        gender: Gender,
        age_group: str | None,
        sanctioning_body: str | None = None,
    ) -> list[TimeStandard]:
        """Find applicable time standards for a swimmer.

        Args:
            gender: Swimmer's gender
            age_group: Swimmer's age group (e.g., "15-18")
            sanctioning_body: Optional filter by sanctioning body

        Returns:
            List of applicable TimeStandards
        """
        query = self.table.select("*, events(*)").eq("gender", gender.value)

        # Include both age-specific and open standards
        if age_group:
            query = query.or_(f"age_group.eq.{age_group},age_group.is.null")

        if sanctioning_body:
            query = query.eq("sanctioning_body", sanctioning_body)

        result = query.execute()
        return [self._to_model(row) for row in result.data]

    def search(
        self,
        stroke: Stroke | None = None,
        distance: int | None = None,
        course: Course | None = None,
        gender: Gender | None = None,
        age_group: str | None = None,
        sanctioning_body: str | None = None,
        standard_name: str | None = None,
        year: int | None = None,
        limit: int = 100,
    ) -> list[TimeStandard]:
        """Search time standards with multiple filters.

        Args:
            stroke: Filter by stroke
            distance: Filter by distance
            course: Filter by course
            gender: Filter by gender
            age_group: Filter by age group
            sanctioning_body: Filter by sanctioning body
            standard_name: Filter by standard name
            year: Filter by effective year
            limit: Maximum results to return

        Returns:
            List of matching TimeStandards
        """
        query = self.table.select("*, events!inner(*)")

        if stroke:
            query = query.eq("events.stroke", stroke.value)
        if distance:
            query = query.eq("events.distance", distance)
        if course:
            query = query.eq("events.course", course.value)
        if gender:
            query = query.eq("gender", gender.value)
        if age_group:
            query = query.eq("age_group", age_group)
        if sanctioning_body:
            query = query.eq("sanctioning_body", sanctioning_body)
        if standard_name:
            query = query.eq("standard_name", standard_name)
        if year:
            query = query.eq("effective_year", year)

        result = query.limit(limit).execute()
        return [self._to_model(row) for row in result.data]

    def create_with_event(
        self,
        stroke: Stroke,
        distance: int,
        course: Course,
        gender: Gender,
        age_group: str | None,
        standard_name: str,
        cut_level: str,
        sanctioning_body: str,
        time_centiseconds: int,
        effective_year: int,
        qualifying_start: date | None = None,
        qualifying_end: date | None = None,
    ) -> TimeStandard:
        """Create a time standard, finding or creating the event.

        This is a convenience method that handles event lookup/creation.

        Returns:
            The created TimeStandard
        """
        # Find or create the event
        event = self.event_dao.find_or_create(stroke, distance, course)

        # Create the time standard
        ts = TimeStandard(
            event=event,
            gender=gender,
            age_group=age_group,
            standard_name=standard_name,
            cut_level=cut_level,
            sanctioning_body=sanctioning_body,
            time_centiseconds=time_centiseconds,
            effective_year=effective_year,
            qualifying_start=qualifying_start,
            qualifying_end=qualifying_end,
        )

        return self.create(ts)

    def create(self, model: TimeStandard) -> TimeStandard:
        """Create a new time standard.

        Overrides base create to preserve the event object, since
        insert doesn't return joined data.
        """
        data = self._to_db(model)
        result = self.table.insert(data).execute()
        row = result.data[0]

        # Return model with ID populated, preserving the event we already have
        return TimeStandard(
            id=UUID(row["id"]),
            event=model.event,  # Preserve the event object
            gender=model.gender,
            age_group=model.age_group,
            standard_name=model.standard_name,
            cut_level=model.cut_level,
            sanctioning_body=model.sanctioning_body,
            time_centiseconds=model.time_centiseconds,
            qualifying_start=model.qualifying_start,
            qualifying_end=model.qualifying_end,
            effective_year=model.effective_year,
        )

    def _to_model(self, row: dict) -> TimeStandard:
        """Convert database row (with joined event) to TimeStandard model."""
        event_data = row.get("events", {})

        event = Event(
            id=UUID(event_data["id"]) if event_data.get("id") else None,
            stroke=Stroke(event_data["stroke"]),
            distance=event_data["distance"],
            course=Course(event_data["course"]),
        )

        return TimeStandard(
            id=UUID(row["id"]) if row.get("id") else None,
            event=event,
            gender=Gender(row["gender"]),
            age_group=row.get("age_group"),
            standard_name=row["standard_name"],
            cut_level=row["cut_level"],
            sanctioning_body=row["sanctioning_body"],
            time_centiseconds=row["time_centiseconds"],
            qualifying_start=row.get("qualifying_start"),
            qualifying_end=row.get("qualifying_end"),
            effective_year=row["effective_year"],
        )

    def _to_db(self, model: TimeStandard) -> dict:
        """Convert TimeStandard model to database row."""
        # Get event_id - event must have an ID
        event_id = model.event.id
        if not event_id:
            # Try to find the event
            event = self.event_dao.find_by_stroke_distance_course(
                model.event.stroke, model.event.distance, model.event.course
            )
            if event and event.id:
                event_id = event.id
            else:
                event_str = f"{model.event.stroke} {model.event.distance} {model.event.course}"
                raise ValueError(f"Event not found: {event_str}")

        data = {
            "event_id": str(event_id),
            "gender": model.gender.value,
            "age_group": model.age_group,
            "standard_name": model.standard_name,
            "cut_level": model.cut_level,
            "sanctioning_body": model.sanctioning_body,
            "time_centiseconds": model.time_centiseconds,
            "effective_year": model.effective_year,
        }

        if model.id:
            data["id"] = str(model.id)
        if model.qualifying_start:
            data["qualifying_start"] = model.qualifying_start.isoformat()
        if model.qualifying_end:
            data["qualifying_end"] = model.qualifying_end.isoformat()

        return data
