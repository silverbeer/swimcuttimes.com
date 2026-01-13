"""Pydantic schemas for CSV import operations."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, field_validator


class Severity(StrEnum):
    """Validation error severity levels."""

    ERROR = "error"
    WARNING = "warning"


class ValidationError(BaseModel):
    """A single validation error or warning."""

    row_number: int
    field: str
    message: str
    severity: Severity = Severity.ERROR


class ValidationResult(BaseModel):
    """Result of validating a CSV file."""

    valid: bool
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    row_count: int = 0

    def add_error(self, row: int, field: str, message: str) -> None:
        """Add a validation error."""
        self.errors.append(
            ValidationError(
                row_number=row,
                field=field,
                message=message,
                severity=Severity.ERROR,
            )
        )
        self.valid = False

    def add_warning(self, row: int, field: str, message: str) -> None:
        """Add a validation warning (doesn't invalidate)."""
        self.warnings.append(
            ValidationError(
                row_number=row,
                field=field,
                message=message,
                severity=Severity.WARNING,
            )
        )


class RosterRow(BaseModel):
    """A parsed row from the roster CSV file."""

    first_name: str
    last_name: str
    date_of_birth: date
    gender: str  # M or F
    usa_swimming_id: str | None = None
    row_number: int = 0

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Normalize and validate gender."""
        v = v.strip().upper()
        if v not in ("M", "F"):
            raise ValueError("Gender must be M or F")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, v: str) -> str:
        """Strip whitespace from names."""
        return v.strip()

    @field_validator("usa_swimming_id")
    @classmethod
    def strip_usa_id(cls, v: str | None) -> str | None:
        """Strip whitespace and handle empty strings."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class MeetRow(BaseModel):
    """A parsed row from the meets CSV file."""

    name: str
    location: str
    city: str
    state: str | None = None
    country: str = "USA"
    start_date: date
    end_date: date | None = None
    course: str  # scy, scm, lcm
    lanes: int = 8
    indoor: bool = True
    sanctioning_body: str
    meet_type: str  # championship, invitational, dual, time_trial
    row_number: int = 0

    @field_validator("course")
    @classmethod
    def validate_course(cls, v: str) -> str:
        """Normalize and validate course."""
        v = v.strip().lower()
        if v not in ("scy", "scm", "lcm"):
            raise ValueError("Course must be scy, scm, or lcm")
        return v

    @field_validator("meet_type")
    @classmethod
    def validate_meet_type(cls, v: str) -> str:
        """Normalize and validate meet type."""
        v = v.strip().lower()
        valid_types = ("championship", "invitational", "dual", "time_trial")
        if v not in valid_types:
            raise ValueError(f"Meet type must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("lanes")
    @classmethod
    def validate_lanes(cls, v: int) -> int:
        """Validate lane count."""
        if v not in (6, 8, 10):
            raise ValueError("Lanes must be 6, 8, or 10")
        return v

    @field_validator("name", "location", "city", "sanctioning_body")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        return v.strip()

    @field_validator("state", "country")
    @classmethod
    def strip_optional_strings(cls, v: str | None) -> str | None:
        """Strip whitespace from optional string fields."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class TimeRow(BaseModel):
    """A parsed row from the times CSV file."""

    # Swimmer identification (one or both)
    swimmer_first_name: str | None = None
    swimmer_last_name: str | None = None
    usa_swimming_id: str | None = None

    # Event details (separate columns for validation)
    distance: int  # 25, 50, 100, 200, 400, 500, 800, 1000, 1500, 1650
    stroke: str  # free, back, breast, fly, im
    course: str  # scy, scm, lcm

    # Meet
    meet_name: str

    # Time data
    time: str  # "59.45" or "1:23.45"
    splits: str | None = None  # "50:28.27;100:58.44;150:1:29.19"
    swim_date: date

    # Team
    team_name: str

    # Optional competition details
    round: str | None = None  # prelims, finals, etc.
    lane: int | None = None
    place: int | None = None
    official: bool = True
    dq: bool = False
    dq_reason: str | None = None

    row_number: int = 0

    @field_validator("swimmer_first_name", "swimmer_last_name")
    @classmethod
    def strip_swimmer_names(cls, v: str | None) -> str | None:
        """Strip whitespace from swimmer names."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("usa_swimming_id")
    @classmethod
    def strip_usa_id(cls, v: str | None) -> str | None:
        """Strip whitespace and handle empty strings."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("meet_name", "team_name", "time")
    @classmethod
    def strip_required_strings(cls, v: str) -> str:
        """Strip whitespace from required string fields."""
        return v.strip()

    @field_validator("distance")
    @classmethod
    def validate_distance(cls, v: int) -> int:
        """Validate event distance."""
        valid_distances = (25, 50, 100, 200, 400, 500, 800, 1000, 1500, 1650)
        if v not in valid_distances:
            raise ValueError(f"Distance must be one of: {', '.join(str(d) for d in valid_distances)}")
        return v

    @field_validator("stroke")
    @classmethod
    def validate_stroke(cls, v: str) -> str:
        """Normalize and validate stroke."""
        v = v.strip().lower()
        # Support common aliases
        stroke_aliases = {
            "free": "freestyle",
            "freestyle": "freestyle",
            "fr": "freestyle",
            "back": "backstroke",
            "backstroke": "backstroke",
            "bk": "backstroke",
            "breast": "breaststroke",
            "breaststroke": "breaststroke",
            "br": "breaststroke",
            "fly": "butterfly",
            "butterfly": "butterfly",
            "fl": "butterfly",
            "im": "im",
            "medley": "im",
        }
        normalized = stroke_aliases.get(v)
        if normalized is None:
            valid = ("free", "back", "breast", "fly", "im")
            raise ValueError(f"Stroke must be one of: {', '.join(valid)}")
        return normalized

    @field_validator("course")
    @classmethod
    def validate_course(cls, v: str) -> str:
        """Normalize and validate course."""
        v = v.strip().lower()
        if v not in ("scy", "scm", "lcm"):
            raise ValueError("Course must be scy, scm, or lcm")
        return v

    @field_validator("splits")
    @classmethod
    def strip_splits(cls, v: str | None) -> str | None:
        """Strip whitespace from splits."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    @field_validator("round")
    @classmethod
    def validate_round(cls, v: str | None) -> str | None:
        """Normalize and validate round."""
        if v is None:
            return None
        v = v.strip().lower()
        if not v:
            return None
        valid_rounds = ("prelims", "finals", "consolation", "bonus_finals", "time_trial")
        if v not in valid_rounds:
            raise ValueError(f"Round must be one of: {', '.join(valid_rounds)}")
        return v

    @field_validator("lane")
    @classmethod
    def validate_lane(cls, v: int | None) -> int | None:
        """Validate lane number."""
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Lane must be between 1 and 10")
        return v

    @field_validator("dq_reason")
    @classmethod
    def strip_dq_reason(cls, v: str | None) -> str | None:
        """Strip whitespace from DQ reason."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    def has_swimmer_identifier(self) -> bool:
        """Check if row has a valid swimmer identifier."""
        has_usa_id = self.usa_swimming_id is not None
        has_name = self.swimmer_first_name is not None and self.swimmer_last_name is not None
        return has_usa_id or has_name

    def get_event_string(self) -> str:
        """Get event as a string like '100 Free SCY'."""
        stroke_display = {
            "freestyle": "Free",
            "backstroke": "Back",
            "breaststroke": "Breast",
            "butterfly": "Fly",
            "im": "IM",
        }
        return f"{self.distance} {stroke_display.get(self.stroke, self.stroke)} {self.course.upper()}"


class ImportAction(StrEnum):
    """Action taken during import."""

    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"


class ImportResultItem(BaseModel):
    """Result for a single imported row."""

    row_number: int
    action: ImportAction
    entity_type: str  # swimmer, meet, team, swim_time
    entity_id: str | None = None
    message: str | None = None


class ImportResult(BaseModel):
    """Result of an import operation."""

    success: bool
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    items: list[ImportResultItem] = []
    errors: list[ValidationError] = []

    def add_created(
        self, row: int, entity_type: str, entity_id: str, message: str | None = None
    ) -> None:
        """Record a created entity."""
        self.items.append(
            ImportResultItem(
                row_number=row,
                action=ImportAction.CREATED,
                entity_type=entity_type,
                entity_id=entity_id,
                message=message,
            )
        )
        self.created_count += 1

    def add_updated(
        self, row: int, entity_type: str, entity_id: str, message: str | None = None
    ) -> None:
        """Record an updated entity."""
        self.items.append(
            ImportResultItem(
                row_number=row,
                action=ImportAction.UPDATED,
                entity_type=entity_type,
                entity_id=entity_id,
                message=message,
            )
        )
        self.updated_count += 1

    def add_skipped(
        self, row: int, entity_type: str, message: str | None = None
    ) -> None:
        """Record a skipped row."""
        self.items.append(
            ImportResultItem(
                row_number=row,
                action=ImportAction.SKIPPED,
                entity_type=entity_type,
                message=message,
            )
        )
        self.skipped_count += 1

    def add_error(self, row: int, field: str, message: str) -> None:
        """Record an error during import."""
        self.errors.append(
            ValidationError(
                row_number=row,
                field=field,
                message=message,
                severity=Severity.ERROR,
            )
        )
        self.error_count += 1
        self.success = False
