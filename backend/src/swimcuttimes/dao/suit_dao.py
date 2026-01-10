"""Data Access Objects for Racing Suits."""

from datetime import date
from uuid import UUID

from supabase import Client

from swimcuttimes.dao.base import BaseDAO
from swimcuttimes.models.suit import SuitCondition, SuitModel, SuitType, SwimmerSuit
from swimcuttimes.models.swimmer import Gender


class SuitModelDAO(BaseDAO[SuitModel]):
    """DAO for SuitModel entities (catalog of racing suits)."""

    table_name = "suit_models"
    model_class = SuitModel

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_brand(self, brand: str) -> list[SuitModel]:
        """Find suit models by brand (case-insensitive).

        Args:
            brand: Brand name to search for

        Returns:
            List of matching SuitModels
        """
        result = self.table.select("*").ilike("brand", f"%{brand}%").execute()
        return [self._to_model(row) for row in result.data]

    def find_by_gender(self, gender: Gender) -> list[SuitModel]:
        """Find suit models by gender.

        Args:
            gender: Gender filter

        Returns:
            List of SuitModels for that gender
        """
        result = self.table.select("*").eq("gender", gender.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_tech_suits(self) -> list[SuitModel]:
        """Find all tech suits.

        Returns:
            List of tech suit SuitModels
        """
        result = self.table.select("*").eq("is_tech_suit", True).execute()
        return [self._to_model(row) for row in result.data]

    def find_regular_suits(self) -> list[SuitModel]:
        """Find all regular racing suits.

        Returns:
            List of regular racing suit SuitModels
        """
        result = self.table.select("*").eq("is_tech_suit", False).execute()
        return [self._to_model(row) for row in result.data]

    def find_fina_approved(self) -> list[SuitModel]:
        """Find all FINA approved suits.

        Returns:
            List of FINA approved SuitModels
        """
        result = self.table.select("*").eq("fina_approved", True).execute()
        return [self._to_model(row) for row in result.data]

    def search(
        self,
        brand: str | None = None,
        model_name: str | None = None,
        suit_type: SuitType | None = None,
        is_tech_suit: bool | None = None,
        gender: Gender | None = None,
        fina_approved: bool | None = None,
        limit: int = 100,
    ) -> list[SuitModel]:
        """Search suit models with optional filters.

        Args:
            brand: Filter by brand (partial match)
            model_name: Filter by model name (partial match)
            suit_type: Filter by suit type
            is_tech_suit: Filter by tech suit vs regular
            gender: Filter by gender
            fina_approved: Filter by FINA approval status
            limit: Maximum results

        Returns:
            List of matching SuitModels
        """
        query = self.table.select("*")

        if brand:
            query = query.ilike("brand", f"%{brand}%")
        if model_name:
            query = query.ilike("model_name", f"%{model_name}%")
        if suit_type:
            query = query.eq("suit_type", suit_type.value)
        if is_tech_suit is not None:
            query = query.eq("is_tech_suit", is_tech_suit)
        if gender:
            query = query.eq("gender", gender.value)
        if fina_approved is not None:
            query = query.eq("fina_approved", fina_approved)

        result = query.limit(limit).order("brand").order("model_name").execute()
        return [self._to_model(row) for row in result.data]

    def _to_model(self, row: dict) -> SuitModel:
        """Convert database row to SuitModel."""
        return SuitModel(
            id=UUID(row["id"]) if row.get("id") else None,
            brand=row["brand"],
            model_name=row["model_name"],
            suit_type=SuitType(row["suit_type"]),
            is_tech_suit=row.get("is_tech_suit", False),
            gender=Gender(row["gender"]),
            release_year=row.get("release_year"),
            msrp_cents=row.get("msrp_cents"),
            expected_races_peak=row.get("expected_races_peak", 10),
            expected_races_total=row.get("expected_races_total", 30),
            fina_approved=row.get("fina_approved", True),
            notes=row.get("notes"),
        )

    def _to_db(self, model: SuitModel) -> dict:
        """Convert SuitModel to database row."""
        data = {
            "brand": model.brand,
            "model_name": model.model_name,
            "suit_type": model.suit_type.value,
            "is_tech_suit": model.is_tech_suit,
            "gender": model.gender.value,
            "expected_races_peak": model.expected_races_peak,
            "expected_races_total": model.expected_races_total,
            "fina_approved": model.fina_approved,
        }

        if model.id:
            data["id"] = str(model.id)
        if model.release_year:
            data["release_year"] = model.release_year
        if model.msrp_cents:
            data["msrp_cents"] = model.msrp_cents
        if model.notes:
            data["notes"] = model.notes

        return data


class SwimmerSuitDAO(BaseDAO[SwimmerSuit]):
    """DAO for SwimmerSuit entities (swimmer's suit inventory)."""

    table_name = "swimmer_suits"
    model_class = SwimmerSuit

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_swimmer(self, swimmer_id: UUID) -> list[SwimmerSuit]:
        """Find all suits for a swimmer (including retired).

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of all SwimmerSuits
        """
        result = self.table.select("*").eq("swimmer_id", str(swimmer_id)).execute()
        return [self._to_model(row) for row in result.data]

    def find_active_by_swimmer(self, swimmer_id: UUID) -> list[SwimmerSuit]:
        """Find active (non-retired) suits for a swimmer.

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of active SwimmerSuits
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .neq("condition", "retired")
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_suit_model(self, suit_model_id: UUID) -> list[SwimmerSuit]:
        """Find all swimmer suits of a specific model.

        Args:
            suit_model_id: The suit model's UUID

        Returns:
            List of SwimmerSuits of that model
        """
        result = self.table.select("*").eq("suit_model_id", str(suit_model_id)).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_condition(
        self, swimmer_id: UUID, condition: SuitCondition
    ) -> list[SwimmerSuit]:
        """Find suits by condition for a swimmer.

        Args:
            swimmer_id: The swimmer's UUID
            condition: The suit condition

        Returns:
            List of SwimmerSuits in that condition
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .eq("condition", condition.value)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def increment_wear_count(self, id: UUID) -> SwimmerSuit | None:
        """Increment the wear count for a suit.

        Args:
            id: The SwimmerSuit's UUID

        Returns:
            Updated SwimmerSuit or None if not found
        """
        # Get current suit
        current = self.get_by_id(id)
        if not current:
            return None

        result = (
            self.table.update({"wear_count": current.wear_count + 1})
            .eq("id", str(id))
            .execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def increment_race_count(self, id: UUID) -> SwimmerSuit | None:
        """Increment the race count for a suit.

        Note: This is also done automatically by a database trigger
        when a swim_time is inserted with this suit_id.

        Args:
            id: The SwimmerSuit's UUID

        Returns:
            Updated SwimmerSuit or None if not found
        """
        # Get current suit
        current = self.get_by_id(id)
        if not current:
            return None

        result = (
            self.table.update({"race_count": current.race_count + 1})
            .eq("id", str(id))
            .execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def update_condition(self, id: UUID, condition: SuitCondition) -> SwimmerSuit | None:
        """Update the condition of a suit.

        Args:
            id: The SwimmerSuit's UUID
            condition: The new condition

        Returns:
            Updated SwimmerSuit or None if not found
        """
        result = (
            self.table.update({"condition": condition.value}).eq("id", str(id)).execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def retire_suit(
        self, id: UUID, retirement_reason: str | None = None, retired_date: date | None = None
    ) -> SwimmerSuit | None:
        """Retire a suit.

        Args:
            id: The SwimmerSuit's UUID
            retirement_reason: Optional reason for retirement
            retired_date: Date of retirement (defaults to today)

        Returns:
            Updated SwimmerSuit or None if not found
        """
        data = {
            "condition": SuitCondition.RETIRED.value,
            "retired_date": (retired_date or date.today()).isoformat(),
        }
        if retirement_reason:
            data["retirement_reason"] = retirement_reason

        result = self.table.update(data).eq("id", str(id)).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def partial_update(self, id: UUID, updates: dict) -> SwimmerSuit | None:
        """Update specific fields of a swimmer suit.

        Args:
            id: SwimmerSuit UUID
            updates: Dictionary of field names to new values

        Returns:
            Updated SwimmerSuit or None if not found
        """
        # Filter out None values
        data = {k: v for k, v in updates.items() if v is not None}

        if not data:
            return self.get_by_id(id)

        # Convert enums to values
        if "condition" in data and isinstance(data["condition"], SuitCondition):
            data["condition"] = data["condition"].value

        # Convert dates to ISO format
        for date_field in ["purchase_date", "retired_date"]:
            if date_field in data and hasattr(data[date_field], "isoformat"):
                data[date_field] = data[date_field].isoformat()

        result = self.table.update(data).eq("id", str(id)).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def _to_model(self, row: dict) -> SwimmerSuit:
        """Convert database row to SwimmerSuit model."""
        return SwimmerSuit(
            id=UUID(row["id"]) if row.get("id") else None,
            swimmer_id=UUID(row["swimmer_id"]),
            suit_model_id=UUID(row["suit_model_id"]),
            nickname=row.get("nickname"),
            size=row.get("size"),
            color=row.get("color"),
            purchase_date=(
                date.fromisoformat(row["purchase_date"]) if row.get("purchase_date") else None
            ),
            purchase_price_cents=row.get("purchase_price_cents"),
            purchase_location=row.get("purchase_location"),
            wear_count=row.get("wear_count", 0),
            race_count=row.get("race_count", 0),
            condition=SuitCondition(row.get("condition", "new")),
            retired_date=(
                date.fromisoformat(row["retired_date"]) if row.get("retired_date") else None
            ),
            retirement_reason=row.get("retirement_reason"),
        )

    def _to_db(self, model: SwimmerSuit) -> dict:
        """Convert SwimmerSuit model to database row."""
        data = {
            "swimmer_id": str(model.swimmer_id),
            "suit_model_id": str(model.suit_model_id),
            "wear_count": model.wear_count,
            "race_count": model.race_count,
            "condition": model.condition.value,
        }

        if model.id:
            data["id"] = str(model.id)
        if model.nickname:
            data["nickname"] = model.nickname
        if model.size:
            data["size"] = model.size
        if model.color:
            data["color"] = model.color
        if model.purchase_date:
            data["purchase_date"] = model.purchase_date.isoformat()
        if model.purchase_price_cents:
            data["purchase_price_cents"] = model.purchase_price_cents
        if model.purchase_location:
            data["purchase_location"] = model.purchase_location
        if model.retired_date:
            data["retired_date"] = model.retired_date.isoformat()
        if model.retirement_reason:
            data["retirement_reason"] = model.retirement_reason

        return data
