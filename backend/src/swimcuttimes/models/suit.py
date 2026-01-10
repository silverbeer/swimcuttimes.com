"""Racing suit models."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, computed_field

from swimcuttimes.models.swimmer import Gender


class SuitType(StrEnum):
    """Type of racing suit."""

    JAMMER = "jammer"  # Men's knee-length suit
    KNEESKIN = "kneeskin"  # Women's knee-length suit
    BRIEF = "brief"  # Sprint suit (men or women)


class SuitCondition(StrEnum):
    """Condition of a swimmer's suit."""

    NEW = "new"
    GOOD = "good"
    WORN = "worn"
    RETIRED = "retired"


class SuitModel(BaseModel):
    """A racing suit product in the catalog.

    Represents a specific suit model from a manufacturer (e.g., Speedo LZR Pure Intent).
    Both tech suits ($200-$500+) and regular racing suits ($30-$100) are tracked.
    """

    id: UUID | None = None
    brand: str  # e.g., "Speedo", "Arena", "TYR"
    model_name: str  # e.g., "LZR Pure Intent", "Carbon Core FX"
    suit_type: SuitType
    is_tech_suit: bool = False  # True for tech suits, False for regular racing suits
    gender: Gender
    release_year: int | None = None
    msrp_cents: int | None = None  # Manufacturer's suggested retail price in cents
    expected_races_peak: int = 10  # Races at peak performance
    expected_races_total: int = 30  # Total expected lifespan in races
    fina_approved: bool = True  # Whether suit is legal for sanctioned competition
    notes: str | None = None

    def __str__(self) -> str:
        return f"{self.brand} {self.model_name}"

    @computed_field
    @property
    def msrp_formatted(self) -> str | None:
        """Format MSRP as currency string."""
        if self.msrp_cents is None:
            return None
        dollars = self.msrp_cents / 100
        return f"${dollars:.2f}"

    @computed_field
    @property
    def suit_category(self) -> str:
        """Human-readable category."""
        return "Tech Suit" if self.is_tech_suit else "Racing Suit"


class SwimmerSuit(BaseModel):
    """An individual racing suit owned by a swimmer.

    Tracks the specific suit instance, its usage history, condition,
    and purchase details.
    """

    id: UUID | None = None
    swimmer_id: UUID
    suit_model_id: UUID
    nickname: str | None = None  # e.g., "Lucky Suit", "Championship Suit"
    size: str | None = None  # e.g., "26", "28", "30"
    color: str | None = None  # e.g., "Black/Gold", "Navy"
    purchase_date: date | None = None
    purchase_price_cents: int | None = None  # Actual price paid
    purchase_location: str | None = None  # e.g., "SwimOutlet", "Dick's", "Team order"
    wear_count: int = 0  # Total times worn
    race_count: int = 0  # Number of races
    condition: SuitCondition = SuitCondition.NEW
    retired_date: date | None = None
    retirement_reason: str | None = None  # e.g., "Lost compression", "Seam rip"

    def __str__(self) -> str:
        if self.nickname:
            return self.nickname
        return f"Suit {self.id}"

    @computed_field
    @property
    def is_retired(self) -> bool:
        """Check if suit is retired."""
        return self.condition == SuitCondition.RETIRED

    @computed_field
    @property
    def is_current(self) -> bool:
        """Check if suit is currently active (not retired)."""
        return self.condition != SuitCondition.RETIRED

    @computed_field
    @property
    def purchase_price_formatted(self) -> str | None:
        """Format purchase price as currency string."""
        if self.purchase_price_cents is None:
            return None
        dollars = self.purchase_price_cents / 100
        return f"${dollars:.2f}"

    def life_percentage(self, expected_races_total: int) -> float:
        """Calculate percentage of expected lifespan used.

        Args:
            expected_races_total: Expected total races from suit model

        Returns:
            Percentage of life used (0-100+)
        """
        if expected_races_total <= 0:
            return 0.0
        return (self.race_count / expected_races_total) * 100

    def remaining_races(self, expected_races_total: int) -> int:
        """Calculate estimated remaining races.

        Args:
            expected_races_total: Expected total races from suit model

        Returns:
            Estimated remaining races (can be negative if overused)
        """
        return expected_races_total - self.race_count

    def is_past_peak(self, expected_races_peak: int) -> bool:
        """Check if suit is past peak performance.

        Args:
            expected_races_peak: Expected races at peak from suit model

        Returns:
            True if suit has exceeded peak race count
        """
        return self.race_count >= expected_races_peak
