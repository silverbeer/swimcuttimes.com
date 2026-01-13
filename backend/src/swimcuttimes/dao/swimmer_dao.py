"""Data Access Object for Swimmers."""

from datetime import date
from uuid import UUID

from supabase import Client
from swimcuttimes.dao.base import BaseDAO
from swimcuttimes.models.swimmer import Gender, Swimmer


class SwimmerDAO(BaseDAO[Swimmer]):
    """DAO for Swimmer entities."""

    table_name = "swimmers"
    model_class = Swimmer

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_name(self, first_name: str, last_name: str) -> list[Swimmer]:
        """Find swimmers by name.

        Args:
            first_name: First name (case-insensitive)
            last_name: Last name (case-insensitive)

        Returns:
            List of matching Swimmers
        """
        result = (
            self.table.select("*")
            .ilike("first_name", first_name)
            .ilike("last_name", last_name)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_last_name(self, last_name: str) -> list[Swimmer]:
        """Find swimmers by last name.

        Args:
            last_name: Last name (case-insensitive)

        Returns:
            List of matching Swimmers
        """
        result = self.table.select("*").ilike("last_name", last_name).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_user_id(self, user_id: UUID) -> Swimmer | None:
        """Find a swimmer linked to a user account.

        Args:
            user_id: The Supabase Auth user ID

        Returns:
            The Swimmer or None if not found
        """
        result = self.table.select("*").eq("user_id", str(user_id)).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def find_by_usa_swimming_id(self, usa_swimming_id: str) -> Swimmer | None:
        """Find a swimmer by USA Swimming ID.

        Args:
            usa_swimming_id: The USA Swimming member ID

        Returns:
            The Swimmer or None if not found
        """
        result = self.table.select("*").eq("usa_swimming_id", usa_swimming_id).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def find_by_name_and_dob(
        self, first_name: str, last_name: str, date_of_birth: date
    ) -> Swimmer | None:
        """Find a swimmer by exact name and date of birth.

        Args:
            first_name: First name (case-insensitive)
            last_name: Last name (case-insensitive)
            date_of_birth: Date of birth

        Returns:
            The Swimmer or None if not found
        """
        result = (
            self.table.select("*")
            .ilike("first_name", first_name)
            .ilike("last_name", last_name)
            .eq("date_of_birth", date_of_birth.isoformat())
            .execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def find_or_create(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        gender: Gender,
        usa_swimming_id: str | None = None,
    ) -> tuple[Swimmer, bool]:
        """Find an existing swimmer or create a new one.

        Matching priority:
        1. USA Swimming ID (if provided)
        2. first_name + last_name + date_of_birth

        Args:
            first_name: Swimmer's first name
            last_name: Swimmer's last name
            date_of_birth: Swimmer's date of birth
            gender: Swimmer's gender
            usa_swimming_id: Optional USA Swimming member ID

        Returns:
            Tuple of (swimmer, was_created) where was_created is True if new
        """
        # Try to find by USA Swimming ID first (most reliable)
        if usa_swimming_id:
            existing = self.find_by_usa_swimming_id(usa_swimming_id)
            if existing:
                return (existing, False)

        # Try to find by name + DOB
        existing = self.find_by_name_and_dob(first_name, last_name, date_of_birth)
        if existing:
            # If we have a USA Swimming ID and the existing record doesn't, update it
            if usa_swimming_id and not existing.usa_swimming_id:
                self.partial_update(existing.id, {"usa_swimming_id": usa_swimming_id})
                existing.usa_swimming_id = usa_swimming_id
            return (existing, False)

        # Create new swimmer
        new_swimmer = Swimmer(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            gender=gender,
            usa_swimming_id=usa_swimming_id,
        )
        created = self.create(new_swimmer)
        return (created, True)

    def find_by_gender(self, gender: Gender) -> list[Swimmer]:
        """Find all swimmers of a specific gender.

        Args:
            gender: The gender to filter by

        Returns:
            List of Swimmers
        """
        result = self.table.select("*").eq("gender", gender.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_age_range(
        self, min_age: int, max_age: int, as_of_date: date | None = None
    ) -> list[Swimmer]:
        """Find swimmers within an age range.

        Args:
            min_age: Minimum age (inclusive)
            max_age: Maximum age (inclusive)
            as_of_date: Date to calculate age (defaults to today)

        Returns:
            List of Swimmers in the age range
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Calculate birth date range
        max_birth_date = date(as_of_date.year - min_age, as_of_date.month, as_of_date.day)
        min_birth_date = date(as_of_date.year - max_age - 1, as_of_date.month, as_of_date.day)

        result = (
            self.table.select("*")
            .gte("date_of_birth", min_birth_date.isoformat())
            .lte("date_of_birth", max_birth_date.isoformat())
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def partial_update(self, id: UUID, updates: dict) -> Swimmer | None:
        """Update specific fields of a swimmer.

        Args:
            id: Swimmer UUID
            updates: Dictionary of field names to new values

        Returns:
            Updated Swimmer or None if not found
        """
        # Filter out None values
        data = {k: v for k, v in updates.items() if v is not None}

        if not data:
            # No updates provided, return current swimmer
            return self.get_by_id(id)

        # Convert types for database
        if "date_of_birth" in data and isinstance(data["date_of_birth"], date):
            data["date_of_birth"] = data["date_of_birth"].isoformat()
        if "gender" in data and isinstance(data["gender"], Gender):
            data["gender"] = data["gender"].value
        if "user_id" in data and isinstance(data["user_id"], UUID):
            data["user_id"] = str(data["user_id"])

        result = self.table.update(data).eq("id", str(id)).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def search(
        self,
        name: str | None = None,
        gender: Gender | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        limit: int = 100,
    ) -> list[Swimmer]:
        """Search swimmers with multiple filters.

        Args:
            name: Search in first or last name (partial match)
            gender: Filter by gender
            min_age: Minimum age filter
            max_age: Maximum age filter
            limit: Maximum results

        Returns:
            List of matching Swimmers
        """
        query = self.table.select("*")

        if name:
            # Search in both first and last name
            query = query.or_(f"first_name.ilike.%{name}%,last_name.ilike.%{name}%")

        if gender:
            query = query.eq("gender", gender.value)

        if min_age is not None or max_age is not None:
            today = date.today()
            if max_age is not None:
                min_birth = date(today.year - max_age - 1, today.month, today.day)
                query = query.gte("date_of_birth", min_birth.isoformat())
            if min_age is not None:
                max_birth = date(today.year - min_age, today.month, today.day)
                query = query.lte("date_of_birth", max_birth.isoformat())

        result = query.limit(limit).execute()
        return [self._to_model(row) for row in result.data]

    def _to_model(self, row: dict) -> Swimmer:
        """Convert database row to Swimmer model."""
        return Swimmer(
            id=row["id"] if row.get("id") else None,  # Short ID (TEXT), not UUID
            first_name=row["first_name"],
            last_name=row["last_name"],
            date_of_birth=date.fromisoformat(row["date_of_birth"]),
            gender=Gender(row["gender"]),
            user_id=UUID(row["user_id"]) if row.get("user_id") else None,  # Still UUID (references auth.users)
            usa_swimming_id=row.get("usa_swimming_id"),
            swimcloud_url=row.get("swimcloud_url"),
        )

    def _to_db(self, model: Swimmer) -> dict:
        """Convert Swimmer model to database row."""
        data = {
            "first_name": model.first_name,
            "last_name": model.last_name,
            "date_of_birth": model.date_of_birth.isoformat(),
            "gender": model.gender.value,
        }

        if model.id:
            data["id"] = str(model.id)
        if model.user_id:
            data["user_id"] = str(model.user_id)
        if model.usa_swimming_id:
            data["usa_swimming_id"] = model.usa_swimming_id
        if model.swimcloud_url:
            data["swimcloud_url"] = model.swimcloud_url

        return data
