"""Service for importing swim meet data from CSV files."""

import csv
from datetime import date
from pathlib import Path

from swimcuttimes.dao.event_dao import EventDAO
from swimcuttimes.dao.meet_dao import MeetDAO
from swimcuttimes.dao.swim_time_dao import SwimTimeDAO
from swimcuttimes.dao.swimmer_dao import SwimmerDAO
from swimcuttimes.dao.team_dao import TeamDAO
from swimcuttimes.models.event import Course
from swimcuttimes.models.meet import MeetType
from swimcuttimes.models.swim_time import Round
from swimcuttimes.models.swimmer import Gender
from swimcuttimes.models.team import TeamType
from swimcuttimes.models.event import Stroke
from swimcuttimes.services.event_parser import (
    parse_splits_string,
    parse_time_string,
)
from swimcuttimes.services.import_schemas import (
    ImportResult,
    MeetRow,
    RosterRow,
    Severity,
    TimeRow,
    ValidationError,
    ValidationResult,
)


class ImportService:
    """Service for importing swim meet data from CSV files."""

    def __init__(
        self,
        swimmer_dao: SwimmerDAO | None = None,
        meet_dao: MeetDAO | None = None,
        team_dao: TeamDAO | None = None,
        event_dao: EventDAO | None = None,
        swim_time_dao: SwimTimeDAO | None = None,
    ):
        self.swimmer_dao = swimmer_dao or SwimmerDAO()
        self.meet_dao = meet_dao or MeetDAO()
        self.team_dao = team_dao or TeamDAO()
        self.event_dao = event_dao or EventDAO()
        self.swim_time_dao = swim_time_dao or SwimTimeDAO()

    # =========================================================================
    # CSV Parsing
    # =========================================================================

    def parse_roster_csv(self, csv_path: Path) -> tuple[list[RosterRow], list[ValidationError]]:
        """Parse a roster CSV file into RosterRow objects.

        Args:
            csv_path: Path to the CSV file

        Returns:
            Tuple of (rows, parse_errors)
        """
        rows: list[RosterRow] = []
        errors: list[ValidationError] = []

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Parse date
                    dob_str = row.get("date_of_birth", "").strip()
                    if not dob_str:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="date_of_birth",
                                message="Date of birth is required",
                            )
                        )
                        continue

                    try:
                        dob = date.fromisoformat(dob_str)
                    except ValueError:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="date_of_birth",
                                message=f"Invalid date format: '{dob_str}'. Expected YYYY-MM-DD",
                            )
                        )
                        continue

                    roster_row = RosterRow(
                        first_name=row.get("first_name", ""),
                        last_name=row.get("last_name", ""),
                        date_of_birth=dob,
                        gender=row.get("gender", ""),
                        usa_swimming_id=row.get("usa_swimming_id"),
                        row_number=row_num,
                    )
                    rows.append(roster_row)

                except Exception as e:
                    errors.append(
                        ValidationError(
                            row_number=row_num,
                            field="row",
                            message=str(e),
                        )
                    )

        return rows, errors

    def parse_meets_csv(self, csv_path: Path) -> tuple[list[MeetRow], list[ValidationError]]:
        """Parse a meets CSV file into MeetRow objects.

        Args:
            csv_path: Path to the CSV file

        Returns:
            Tuple of (rows, parse_errors)
        """
        rows: list[MeetRow] = []
        errors: list[ValidationError] = []

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Parse dates
                    start_str = row.get("start_date", "").strip()
                    if not start_str:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="start_date",
                                message="Start date is required",
                            )
                        )
                        continue

                    try:
                        start_date = date.fromisoformat(start_str)
                    except ValueError:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="start_date",
                                message=f"Invalid date format: '{start_str}'",
                            )
                        )
                        continue

                    end_str = row.get("end_date", "").strip()
                    end_date = None
                    if end_str:
                        try:
                            end_date = date.fromisoformat(end_str)
                        except ValueError:
                            errors.append(
                                ValidationError(
                                    row_number=row_num,
                                    field="end_date",
                                    message=f"Invalid date format: '{end_str}'",
                                )
                            )
                            continue

                    # Parse optional integer fields
                    lanes_str = row.get("lanes", "8").strip()
                    lanes = int(lanes_str) if lanes_str else 8

                    # Parse boolean fields
                    indoor_str = row.get("indoor", "true").strip().lower()
                    indoor = indoor_str in ("true", "1", "yes", "")

                    meet_row = MeetRow(
                        name=row.get("name", ""),
                        location=row.get("location", ""),
                        city=row.get("city", ""),
                        state=row.get("state"),
                        country=row.get("country", "USA"),
                        start_date=start_date,
                        end_date=end_date,
                        course=row.get("course", ""),
                        lanes=lanes,
                        indoor=indoor,
                        sanctioning_body=row.get("sanctioning_body", ""),
                        meet_type=row.get("meet_type", ""),
                        row_number=row_num,
                    )
                    rows.append(meet_row)

                except Exception as e:
                    errors.append(
                        ValidationError(
                            row_number=row_num,
                            field="row",
                            message=str(e),
                        )
                    )

        return rows, errors

    def parse_times_csv(self, csv_path: Path) -> tuple[list[TimeRow], list[ValidationError]]:
        """Parse a times CSV file into TimeRow objects.

        Args:
            csv_path: Path to the CSV file

        Returns:
            Tuple of (rows, parse_errors)
        """
        rows: list[TimeRow] = []
        errors: list[ValidationError] = []

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Parse date
                    swim_date_str = row.get("swim_date", "").strip()
                    if not swim_date_str:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="swim_date",
                                message="Swim date is required",
                            )
                        )
                        continue

                    try:
                        swim_date = date.fromisoformat(swim_date_str)
                    except ValueError:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="swim_date",
                                message=f"Invalid date format: '{swim_date_str}'",
                            )
                        )
                        continue

                    # Parse distance (required integer)
                    distance_str = row.get("distance", "").strip()
                    if not distance_str:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="distance",
                                message="Distance is required",
                            )
                        )
                        continue

                    try:
                        distance = int(distance_str)
                    except ValueError:
                        errors.append(
                            ValidationError(
                                row_number=row_num,
                                field="distance",
                                message=f"Invalid distance: '{distance_str}'",
                            )
                        )
                        continue

                    # Parse optional integer fields
                    lane_str = row.get("lane", "").strip()
                    lane = int(lane_str) if lane_str else None

                    place_str = row.get("place", "").strip()
                    place = int(place_str) if place_str else None

                    # Parse boolean fields
                    official_str = row.get("official", "true").strip().lower()
                    official = official_str in ("true", "1", "yes", "")

                    dq_str = row.get("dq", "false").strip().lower()
                    dq = dq_str in ("true", "1", "yes")

                    time_row = TimeRow(
                        swimmer_first_name=row.get("swimmer_first_name"),
                        swimmer_last_name=row.get("swimmer_last_name"),
                        usa_swimming_id=row.get("usa_swimming_id"),
                        distance=distance,
                        stroke=row.get("stroke", ""),
                        course=row.get("course", ""),
                        meet_name=row.get("meet_name", ""),
                        time=row.get("time", ""),
                        splits=row.get("splits"),
                        swim_date=swim_date,
                        team_name=row.get("team_name", ""),
                        round=row.get("round"),
                        lane=lane,
                        place=place,
                        official=official,
                        dq=dq,
                        dq_reason=row.get("dq_reason"),
                        row_number=row_num,
                    )
                    rows.append(time_row)

                except Exception as e:
                    errors.append(
                        ValidationError(
                            row_number=row_num,
                            field="row",
                            message=str(e),
                        )
                    )

        return rows, errors

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_roster(self, rows: list[RosterRow]) -> ValidationResult:
        """Validate roster rows.

        Args:
            rows: List of RosterRow objects

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True, row_count=len(rows))
        seen_swimmers: set[tuple[str, str, date]] = set()

        for row in rows:
            # Required fields
            if not row.first_name:
                result.add_error(row.row_number, "first_name", "First name is required")
            if not row.last_name:
                result.add_error(row.row_number, "last_name", "Last name is required")

            # Date validation
            if row.date_of_birth > date.today():
                result.add_error(
                    row.row_number,
                    "date_of_birth",
                    "Date of birth cannot be in the future",
                )

            # Age warning
            today = date.today()
            age = (
                today.year
                - row.date_of_birth.year
                - ((today.month, today.day) < (row.date_of_birth.month, row.date_of_birth.day))
            )
            if age < 5 or age > 25:
                result.add_warning(
                    row.row_number,
                    "date_of_birth",
                    f"Swimmer age {age} is outside typical range (5-25)",
                )

            # Duplicate detection
            key = (row.first_name.lower(), row.last_name.lower(), row.date_of_birth)
            if key in seen_swimmers:
                result.add_warning(
                    row.row_number,
                    "row",
                    f"Duplicate swimmer: {row.first_name} {row.last_name}",
                )
            seen_swimmers.add(key)

        return result

    def validate_meets(self, rows: list[MeetRow]) -> ValidationResult:
        """Validate meet rows.

        Args:
            rows: List of MeetRow objects

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True, row_count=len(rows))
        seen_meets: set[tuple[str, date]] = set()

        for row in rows:
            # Required fields
            if not row.name:
                result.add_error(row.row_number, "name", "Meet name is required")
            if not row.location:
                result.add_error(row.row_number, "location", "Location is required")
            if not row.city:
                result.add_error(row.row_number, "city", "City is required")
            if not row.sanctioning_body:
                result.add_error(
                    row.row_number, "sanctioning_body", "Sanctioning body is required"
                )
            if not row.meet_type:
                result.add_error(row.row_number, "meet_type", "Meet type is required")

            # Date validation
            if row.end_date and row.end_date < row.start_date:
                result.add_error(
                    row.row_number,
                    "end_date",
                    "End date must be on or after start date",
                )

            # Duplicate detection
            key = (row.name.lower(), row.start_date)
            if key in seen_meets:
                result.add_warning(
                    row.row_number,
                    "name",
                    f"Duplicate meet: {row.name} on {row.start_date}",
                )
            seen_meets.add(key)

        return result

    def validate_times(
        self,
        rows: list[TimeRow],
        roster: list[RosterRow] | None = None,
        meets: list[MeetRow] | None = None,
    ) -> ValidationResult:
        """Validate time rows.

        Args:
            rows: List of TimeRow objects
            roster: Optional roster for swimmer validation
            meets: Optional meets for meet validation

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True, row_count=len(rows))

        # Build lookup tables from roster and meets
        roster_swimmers: set[tuple[str, str]] = set()
        roster_usa_ids: set[str] = set()
        if roster:
            for r in roster:
                roster_swimmers.add((r.first_name.lower(), r.last_name.lower()))
                if r.usa_swimming_id:
                    roster_usa_ids.add(r.usa_swimming_id)

        meet_names: set[str] = set()
        if meets:
            for m in meets:
                meet_names.add(m.name.lower())

        for row in rows:
            # Swimmer identifier check
            if not row.has_swimmer_identifier():
                result.add_error(
                    row.row_number,
                    "swimmer",
                    "Either usa_swimming_id or (swimmer_first_name + swimmer_last_name) required",
                )

            # Required fields
            if not row.meet_name:
                result.add_error(row.row_number, "meet_name", "Meet name is required")
            if not row.time:
                result.add_error(row.row_number, "time", "Time is required")
            if not row.team_name:
                result.add_error(row.row_number, "team_name", "Team name is required")

            # Time format validation
            time_centiseconds = None
            if row.time:
                try:
                    time_centiseconds = parse_time_string(row.time)
                except ValueError as e:
                    result.add_error(row.row_number, "time", str(e))

            # Splits validation (if provided)
            if row.splits and time_centiseconds is not None:
                try:
                    parse_splits_string(row.splits, row.distance, time_centiseconds)
                except ValueError as e:
                    result.add_error(row.row_number, "splits", str(e))

            # Cross-reference validation (if roster/meets provided)
            if roster and row.has_swimmer_identifier():
                swimmer_found = False
                if row.usa_swimming_id and row.usa_swimming_id in roster_usa_ids:
                    swimmer_found = True
                elif row.swimmer_first_name and row.swimmer_last_name:
                    key = (row.swimmer_first_name.lower(), row.swimmer_last_name.lower())
                    if key in roster_swimmers:
                        swimmer_found = True
                if not swimmer_found:
                    swimmer_id = row.usa_swimming_id or f"{row.swimmer_first_name} {row.swimmer_last_name}"
                    result.add_warning(
                        row.row_number,
                        "swimmer",
                        f"Swimmer not found in roster: {swimmer_id}",
                    )

            if meets and row.meet_name:
                if row.meet_name.lower() not in meet_names:
                    result.add_warning(
                        row.row_number,
                        "meet_name",
                        f"Meet not found in meets file: {row.meet_name}",
                    )

        return result

    # =========================================================================
    # Import Operations
    # =========================================================================

    def import_roster(self, rows: list[RosterRow]) -> ImportResult:
        """Import roster rows into the database.

        Args:
            rows: List of validated RosterRow objects

        Returns:
            ImportResult with counts and any errors
        """
        result = ImportResult(success=True)

        for row in rows:
            try:
                gender = Gender(row.gender)
                swimmer, created = self.swimmer_dao.find_or_create(
                    first_name=row.first_name,
                    last_name=row.last_name,
                    date_of_birth=row.date_of_birth,
                    gender=gender,
                    usa_swimming_id=row.usa_swimming_id,
                )

                if created:
                    result.add_created(
                        row.row_number,
                        "swimmer",
                        swimmer.id,
                        f"{swimmer.first_name} {swimmer.last_name}",
                    )
                else:
                    result.add_updated(
                        row.row_number,
                        "swimmer",
                        swimmer.id,
                        f"{swimmer.first_name} {swimmer.last_name} (existing)",
                    )

            except Exception as e:
                result.add_error(row.row_number, "row", str(e))

        return result

    def import_meets(self, rows: list[MeetRow]) -> ImportResult:
        """Import meet rows into the database.

        Args:
            rows: List of validated MeetRow objects

        Returns:
            ImportResult with counts and any errors
        """
        result = ImportResult(success=True)

        for row in rows:
            try:
                course = Course(row.course)
                meet_type = MeetType(row.meet_type)

                meet, created = self.meet_dao.find_or_create(
                    name=row.name,
                    start_date=row.start_date,
                    location=row.location,
                    city=row.city,
                    course=course,
                    sanctioning_body=row.sanctioning_body,
                    meet_type=meet_type,
                    state=row.state,
                    country=row.country,
                    end_date=row.end_date,
                    lanes=row.lanes,
                    indoor=row.indoor,
                )

                if created:
                    result.add_created(
                        row.row_number,
                        "meet",
                        meet.id,
                        f"{meet.name} ({meet.start_date})",
                    )
                else:
                    result.add_updated(
                        row.row_number,
                        "meet",
                        meet.id,
                        f"{meet.name} (existing)",
                    )

            except Exception as e:
                result.add_error(row.row_number, "row", str(e))

        return result

    def import_times(
        self,
        rows: list[TimeRow],
        default_team_type: TeamType = TeamType.CLUB,
        default_sanctioning_body: str = "USA Swimming",
    ) -> ImportResult:
        """Import time rows into the database.

        Args:
            rows: List of validated TimeRow objects
            default_team_type: Default team type when creating teams
            default_sanctioning_body: Default sanctioning body for new teams

        Returns:
            ImportResult with counts and any errors
        """
        result = ImportResult(success=True)

        # Cache for resolved entities
        swimmer_cache: dict[str, str] = {}  # key -> swimmer_id
        meet_cache: dict[str, str] = {}  # meet_name.lower() -> meet_id
        team_cache: dict[str, str] = {}  # team_name.lower() -> team_id
        event_cache: dict[tuple, str] = {}  # (distance, stroke, course) -> event_id

        for row in rows:
            try:
                # Resolve swimmer
                swimmer_id = self._resolve_swimmer(row, swimmer_cache)
                if not swimmer_id:
                    result.add_error(
                        row.row_number,
                        "swimmer",
                        f"Swimmer not found: {row.usa_swimming_id or f'{row.swimmer_first_name} {row.swimmer_last_name}'}",
                    )
                    continue

                # Resolve meet
                meet_id = self._resolve_meet(row.meet_name, meet_cache)
                if not meet_id:
                    result.add_error(
                        row.row_number,
                        "meet_name",
                        f"Meet not found: {row.meet_name}",
                    )
                    continue

                # Resolve team (auto-create if needed)
                team_id = self._resolve_team(
                    row.team_name, team_cache, default_team_type, default_sanctioning_body
                )

                # Resolve event from distance, stroke, course
                event_id = self._resolve_event_from_parts(
                    row.distance, row.stroke, row.course, event_cache
                )
                if not event_id:
                    result.add_error(
                        row.row_number,
                        "event",
                        f"Could not resolve event: {row.distance} {row.stroke} {row.course}",
                    )
                    continue

                # Parse time
                time_centiseconds = parse_time_string(row.time)

                # Parse splits (if provided)
                splits = None
                if row.splits:
                    try:
                        splits = parse_splits_string(
                            row.splits, row.distance, time_centiseconds
                        )
                    except ValueError as e:
                        result.add_error(row.row_number, "splits", str(e))
                        continue

                # Parse round
                round_val = Round(row.round) if row.round else None

                # Upsert the swim time
                swim_time, action = self.swim_time_dao.upsert(
                    swimmer_id=swimmer_id,
                    event_id=event_id,
                    meet_id=meet_id,
                    team_id=team_id,
                    time_centiseconds=time_centiseconds,
                    swim_date=row.swim_date,
                    round=round_val,
                    lane=row.lane,
                    place=row.place,
                    official=row.official,
                    dq=row.dq,
                    dq_reason=row.dq_reason,
                    splits=splits,
                )

                event_display = row.get_event_string()
                if action == "created":
                    result.add_created(
                        row.row_number,
                        "swim_time",
                        swim_time.id,
                        f"{event_display}: {row.time}",
                    )
                else:
                    result.add_updated(
                        row.row_number,
                        "swim_time",
                        swim_time.id,
                        f"{event_display}: {row.time} (updated)",
                    )

            except Exception as e:
                result.add_error(row.row_number, "row", str(e))

        return result

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _resolve_swimmer(
        self, row: TimeRow, cache: dict[str, str]
    ) -> str | None:
        """Resolve a swimmer from a time row."""
        # Build cache key
        if row.usa_swimming_id:
            cache_key = f"usa:{row.usa_swimming_id}"
        elif row.swimmer_first_name and row.swimmer_last_name:
            cache_key = f"name:{row.swimmer_first_name.lower()}:{row.swimmer_last_name.lower()}"
        else:
            return None

        # Check cache
        if cache_key in cache:
            return cache[cache_key]

        # Look up in database
        swimmer = None
        if row.usa_swimming_id:
            swimmer = self.swimmer_dao.find_by_usa_swimming_id(row.usa_swimming_id)
        if not swimmer and row.swimmer_first_name and row.swimmer_last_name:
            swimmers = self.swimmer_dao.find_by_name(
                row.swimmer_first_name, row.swimmer_last_name
            )
            if len(swimmers) == 1:
                swimmer = swimmers[0]
            elif len(swimmers) > 1:
                # Multiple matches - can't determine which one
                return None

        if swimmer:
            cache[cache_key] = swimmer.id
            return swimmer.id

        return None

    def _resolve_meet(self, meet_name: str, cache: dict[str, str]) -> str | None:
        """Resolve a meet by name."""
        cache_key = meet_name.lower()

        if cache_key in cache:
            return cache[cache_key]

        # Look up in database (exact name match)
        meets = self.meet_dao.find_by_name(meet_name)
        if len(meets) == 1:
            cache[cache_key] = meets[0].id
            return meets[0].id
        elif len(meets) > 1:
            # Multiple matches - find exact match
            for m in meets:
                if m.name.lower() == cache_key:
                    cache[cache_key] = m.id
                    return m.id

        return None

    def _resolve_team(
        self,
        team_name: str,
        cache: dict[str, str],
        default_type: TeamType,
        default_sanctioning_body: str,
    ) -> str:
        """Resolve a team by name, creating if necessary."""
        cache_key = team_name.lower()

        if cache_key in cache:
            return cache[cache_key]

        # Find or create team
        team, _ = self.team_dao.find_or_create(
            name=team_name,
            team_type=default_type,
            sanctioning_body=default_sanctioning_body,
        )

        cache[cache_key] = team.id
        return team.id

    def _resolve_event_from_parts(
        self,
        distance: int,
        stroke_str: str,
        course_str: str,
        cache: dict[tuple, str],
    ) -> str | None:
        """Resolve an event from distance, stroke, and course.

        Args:
            distance: Event distance in yards/meters
            stroke_str: Stroke name (normalized by TimeRow validator)
            course_str: Course code (scy, scm, lcm)
            cache: Cache for resolved events

        Returns:
            Event ID or None if resolution fails
        """
        # Map stroke string to Stroke enum
        stroke_map = {
            "freestyle": Stroke.FREESTYLE,
            "backstroke": Stroke.BACKSTROKE,
            "breaststroke": Stroke.BREASTSTROKE,
            "butterfly": Stroke.BUTTERFLY,
            "im": Stroke.IM,
        }
        stroke = stroke_map.get(stroke_str)
        if not stroke:
            return None

        # Map course string to Course enum
        course = Course(course_str)

        cache_key = (distance, stroke, course)

        if cache_key in cache:
            return cache[cache_key]

        # Find or create event
        event = self.event_dao.find_or_create(stroke, distance, course)
        cache[cache_key] = event.id
        return event.id
