"""Swimmer model."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, computed_field


class Gender(StrEnum):
    """Swimmer gender for competition purposes."""

    MALE = "M"
    FEMALE = "F"


class Swimmer(BaseModel):
    """A competitive swimmer."""

    id: str | None = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    user_id: UUID | None = None  # Link to Supabase auth.users (stays UUID)
    usa_swimming_id: str | None = None  # USA Swimming member ID
    swimcloud_url: str | None = None  # e.g., "https://www.swimcloud.com/swimmer/123456/"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def age(self) -> int:
        """Calculate current age."""
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    def age_on_date(self, target_date: date) -> int:
        """Calculate age on a specific date."""
        return (
            target_date.year
            - self.date_of_birth.year
            - (
                (target_date.month, target_date.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    def age_group_on_date(self, target_date: date) -> str:
        """Determine age group on a specific date.

        Common age groups: 10U, 11-12, 13-14, 15-16, 17-18, Open
        """
        age = self.age_on_date(target_date)

        if age <= 10:
            return "10U"
        elif age <= 12:
            return "11-12"
        elif age <= 14:
            return "13-14"
        elif age <= 16:
            return "15-16"
        elif age <= 18:
            return "17-18"
        else:
            return "Open"
