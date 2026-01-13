"""Data Access Object for Meets."""

from datetime import date

from supabase import Client

from swimcuttimes.dao.base import BaseDAO
from swimcuttimes.models.event import Course
from swimcuttimes.models.meet import Meet, MeetType


class MeetDAO(BaseDAO[Meet]):
    """DAO for Meet entities."""

    table_name = "meets"
    model_class = Meet

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_name(self, name: str) -> list[Meet]:
        """Find meets by name (partial match).

        Args:
            name: Meet name to search for

        Returns:
            List of matching Meets
        """
        result = self.table.select("*").ilike("name", f"%{name}%").execute()
        return [self._to_model(row) for row in result.data]

    def find_by_name_and_date(self, name: str, start_date: date) -> Meet | None:
        """Find a meet by exact name and start date.

        Args:
            name: Exact meet name (case-insensitive)
            start_date: The meet start date

        Returns:
            The Meet or None if not found
        """
        result = (
            self.table.select("*")
            .ilike("name", name)
            .eq("start_date", start_date.isoformat())
            .execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def find_or_create(
        self,
        name: str,
        start_date: date,
        location: str,
        city: str,
        course: Course,
        sanctioning_body: str,
        meet_type: MeetType,
        state: str | None = None,
        country: str = "USA",
        end_date: date | None = None,
        lanes: int = 8,
        indoor: bool = True,
    ) -> tuple[Meet, bool]:
        """Find an existing meet or create a new one.

        Matching is done by name + start_date (unique enough for meets).

        Args:
            name: Meet name
            start_date: Meet start date
            location: Venue name
            city: City
            course: Pool course type
            sanctioning_body: Sanctioning organization
            meet_type: Type of meet
            state: State abbreviation (optional)
            country: Country code (default USA)
            end_date: End date for multi-day meets (optional)
            lanes: Number of lanes (default 8)
            indoor: Indoor vs outdoor (default True)

        Returns:
            Tuple of (meet, was_created) where was_created is True if new
        """
        # Try to find existing meet
        existing = self.find_by_name_and_date(name, start_date)
        if existing:
            return (existing, False)

        # Create new meet
        new_meet = Meet(
            name=name,
            start_date=start_date,
            end_date=end_date,
            location=location,
            city=city,
            state=state,
            country=country,
            course=course,
            lanes=lanes,
            indoor=indoor,
            sanctioning_body=sanctioning_body,
            meet_type=meet_type,
        )
        created = self.create(new_meet)
        return (created, True)

    def find_by_date_range(self, start: date, end: date) -> list[Meet]:
        """Find meets within a date range.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of Meets in that date range
        """
        result = (
            self.table.select("*")
            .gte("start_date", start.isoformat())
            .lte("start_date", end.isoformat())
            .order("start_date")
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_course(self, course: Course) -> list[Meet]:
        """Find meets by course type.

        Args:
            course: The course type (SCY, SCM, LCM)

        Returns:
            List of Meets with that course
        """
        result = self.table.select("*").eq("course", course.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_type(self, meet_type: MeetType) -> list[Meet]:
        """Find meets by meet type.

        Args:
            meet_type: The type of meet

        Returns:
            List of Meets of that type
        """
        result = self.table.select("*").eq("meet_type", meet_type.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_sanctioning_body(self, sanctioning_body: str) -> list[Meet]:
        """Find meets by sanctioning body.

        Args:
            sanctioning_body: e.g., "NE Swimming", "USA Swimming"

        Returns:
            List of Meets sanctioned by that body
        """
        result = self.table.select("*").eq("sanctioning_body", sanctioning_body).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_location(self, city: str | None = None, state: str | None = None) -> list[Meet]:
        """Find meets by location.

        Args:
            city: City name (partial match)
            state: State abbreviation

        Returns:
            List of Meets at that location
        """
        query = self.table.select("*")

        if city:
            query = query.ilike("city", f"%{city}%")
        if state:
            query = query.eq("state", state)

        result = query.execute()
        return [self._to_model(row) for row in result.data]

    def find_indoor(self) -> list[Meet]:
        """Find all indoor meets.

        Returns:
            List of indoor Meets
        """
        result = self.table.select("*").eq("indoor", True).execute()
        return [self._to_model(row) for row in result.data]

    def find_outdoor(self) -> list[Meet]:
        """Find all outdoor meets.

        Returns:
            List of outdoor Meets
        """
        result = self.table.select("*").eq("indoor", False).execute()
        return [self._to_model(row) for row in result.data]

    def search(
        self,
        name: str | None = None,
        course: Course | None = None,
        meet_type: MeetType | None = None,
        sanctioning_body: str | None = None,
        start_after: date | None = None,
        start_before: date | None = None,
        indoor: bool | None = None,
        limit: int = 100,
    ) -> list[Meet]:
        """Search meets with multiple filters.

        Args:
            name: Search in meet name
            course: Filter by course
            meet_type: Filter by meet type
            sanctioning_body: Filter by sanctioning body
            start_after: Only meets starting after this date
            start_before: Only meets starting before this date
            indoor: Filter by indoor/outdoor
            limit: Maximum results

        Returns:
            List of matching Meets
        """
        query = self.table.select("*")

        if name:
            query = query.ilike("name", f"%{name}%")
        if course:
            query = query.eq("course", course.value)
        if meet_type:
            query = query.eq("meet_type", meet_type.value)
        if sanctioning_body:
            query = query.eq("sanctioning_body", sanctioning_body)
        if start_after:
            query = query.gte("start_date", start_after.isoformat())
        if start_before:
            query = query.lte("start_date", start_before.isoformat())
        if indoor is not None:
            query = query.eq("indoor", indoor)

        result = query.limit(limit).order("start_date", desc=True).execute()
        return [self._to_model(row) for row in result.data]

    def _to_model(self, row: dict) -> Meet:
        """Convert database row to Meet model."""
        return Meet(
            id=row.get("id"),
            name=row["name"],
            location=row["location"],
            city=row["city"],
            state=row.get("state"),
            country=row.get("country", "USA"),
            start_date=date.fromisoformat(row["start_date"]),
            end_date=date.fromisoformat(row["end_date"]) if row.get("end_date") else None,
            course=Course(row["course"]),
            lanes=row["lanes"],
            indoor=row.get("indoor", True),
            sanctioning_body=row["sanctioning_body"],
            meet_type=MeetType(row["meet_type"]),
        )

    def _to_db(self, model: Meet) -> dict:
        """Convert Meet model to database row."""
        data = {
            "name": model.name,
            "location": model.location,
            "city": model.city,
            "start_date": model.start_date.isoformat(),
            "course": model.course.value,
            "lanes": model.lanes,
            "indoor": model.indoor,
            "sanctioning_body": model.sanctioning_body,
            "meet_type": model.meet_type.value,
        }

        if model.id:
            data["id"] = str(model.id)
        if model.state:
            data["state"] = model.state
        if model.country:
            data["country"] = model.country
        if model.end_date:
            data["end_date"] = model.end_date.isoformat()

        return data
