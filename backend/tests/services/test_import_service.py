"""Tests for import service and related utilities."""

from datetime import date

import pytest

from swimcuttimes.models.event import Course, Stroke
from swimcuttimes.services.event_parser import (
    format_centiseconds,
    format_splits,
    parse_event_string,
    parse_splits_string,
    parse_time_string,
)
from swimcuttimes.services.import_schemas import (
    MeetRow,
    RosterRow,
    TimeRow,
    ValidationResult,
)
from swimcuttimes.services.import_service import ImportService


class TestEventParser:
    """Tests for event string parsing."""

    def test_parse_100_free_scy(self):
        """Parse '100 Free SCY'."""
        distance, stroke, course = parse_event_string("100 Free SCY")
        assert distance == 100
        assert stroke == Stroke.FREESTYLE
        assert course == Course.SCY

    def test_parse_200_im_lcm(self):
        """Parse '200 IM LCM'."""
        distance, stroke, course = parse_event_string("200 IM LCM")
        assert distance == 200
        assert stroke == Stroke.IM
        assert course == Course.LCM

    def test_parse_50_back_with_default_course(self):
        """Parse '50 Back' with default course."""
        distance, stroke, course = parse_event_string("50 Back", default_course=Course.SCY)
        assert distance == 50
        assert stroke == Stroke.BACKSTROKE
        assert course == Course.SCY

    def test_parse_100_breast_scm(self):
        """Parse '100 Breast SCM'."""
        distance, stroke, course = parse_event_string("100 breast scm")
        assert distance == 100
        assert stroke == Stroke.BREASTSTROKE
        assert course == Course.SCM

    def test_parse_200_fly(self):
        """Parse '200 Fly' with default course."""
        distance, stroke, course = parse_event_string("200 Fly", default_course=Course.LCM)
        assert distance == 200
        assert stroke == Stroke.BUTTERFLY
        assert course == Course.LCM

    def test_parse_invalid_event_no_course(self):
        """Error when no course and no default."""
        with pytest.raises(ValueError, match="No course specified"):
            parse_event_string("100 Free")

    def test_parse_invalid_distance(self):
        """Error for invalid distance."""
        with pytest.raises(ValueError, match="Invalid distance"):
            parse_event_string("abc Free SCY")

    def test_parse_invalid_stroke(self):
        """Error for invalid stroke."""
        with pytest.raises(ValueError, match="Invalid stroke"):
            parse_event_string("100 Crawl SCY")

    def test_parse_invalid_course(self):
        """Error for invalid course."""
        with pytest.raises(ValueError, match="Invalid course"):
            parse_event_string("100 Free XYZ")

    def test_parse_stroke_aliases(self):
        """Test various stroke aliases."""
        # Freestyle aliases
        assert parse_event_string("100 free scy")[1] == Stroke.FREESTYLE
        assert parse_event_string("100 freestyle scy")[1] == Stroke.FREESTYLE
        assert parse_event_string("100 fr scy")[1] == Stroke.FREESTYLE

        # Backstroke aliases
        assert parse_event_string("100 back scy")[1] == Stroke.BACKSTROKE
        assert parse_event_string("100 backstroke scy")[1] == Stroke.BACKSTROKE
        assert parse_event_string("100 bk scy")[1] == Stroke.BACKSTROKE

        # Breaststroke aliases
        assert parse_event_string("100 breast scy")[1] == Stroke.BREASTSTROKE
        assert parse_event_string("100 breaststroke scy")[1] == Stroke.BREASTSTROKE
        assert parse_event_string("100 br scy")[1] == Stroke.BREASTSTROKE

        # Butterfly aliases
        assert parse_event_string("100 fly scy")[1] == Stroke.BUTTERFLY
        assert parse_event_string("100 butterfly scy")[1] == Stroke.BUTTERFLY
        assert parse_event_string("100 fl scy")[1] == Stroke.BUTTERFLY


class TestTimeParser:
    """Tests for time string parsing."""

    def test_parse_seconds_only(self):
        """Parse '59.45' -> 5945 centiseconds."""
        assert parse_time_string("59.45") == 5945

    def test_parse_with_minutes(self):
        """Parse '1:23.45' -> 8345 centiseconds."""
        assert parse_time_string("1:23.45") == 8345

    def test_parse_double_minutes(self):
        """Parse '12:34.56' -> 75456 centiseconds."""
        assert parse_time_string("12:34.56") == 75456

    def test_parse_single_digit_centiseconds(self):
        """Parse '25.9' -> 2590 centiseconds (padded)."""
        assert parse_time_string("25.9") == 2590

    def test_parse_leading_zero(self):
        """Parse '0:45.67' -> 4567 centiseconds."""
        assert parse_time_string("0:45.67") == 4567

    def test_format_seconds_only(self):
        """Format 5945 -> '59.45'."""
        assert format_centiseconds(5945) == "59.45"

    def test_format_with_minutes(self):
        """Format 8345 -> '1:23.45'."""
        assert format_centiseconds(8345) == "1:23.45"

    def test_format_double_minutes(self):
        """Format 75456 -> '12:34.56'."""
        assert format_centiseconds(75456) == "12:34.56"

    def test_invalid_time_format(self):
        """Error for invalid time format."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_string("abc")

    def test_invalid_time_no_centiseconds(self):
        """Error for time without decimal."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time_string("59")


class TestSplitsParser:
    """Tests for splits string parsing."""

    def test_parse_simple_splits(self):
        """Parse '50:28.27;100:58.44' for 100m event."""
        splits = parse_splits_string("50:28.27", 100, 5945)
        assert len(splits) == 1
        assert splits[0].distance == 50
        assert splits[0].time_centiseconds == 2827

    def test_parse_multiple_splits(self):
        """Parse multiple splits for 200m event."""
        splits = parse_splits_string("50:28.27;100:58.44;150:1:29.19", 200, 12155)
        assert len(splits) == 3
        assert splits[0].distance == 50
        assert splits[0].time_centiseconds == 2827
        assert splits[1].distance == 100
        assert splits[1].time_centiseconds == 5844
        assert splits[2].distance == 150
        assert splits[2].time_centiseconds == 8919

    def test_parse_empty_splits(self):
        """Empty string returns empty list."""
        splits = parse_splits_string("", 100, 5945)
        assert splits == []

    def test_parse_none_splits(self):
        """None returns empty list."""
        splits = parse_splits_string(None, 100, 5945)
        assert splits == []

    def test_invalid_split_no_colon(self):
        """Error for split without colon."""
        with pytest.raises(ValueError, match="Invalid split format"):
            parse_splits_string("5028.27", 100, 5945)

    def test_invalid_split_distance(self):
        """Error for invalid split distance."""
        with pytest.raises(ValueError, match="Invalid split distance"):
            parse_splits_string("abc:28.27", 100, 5945)

    def test_splits_not_cumulative(self):
        """Error when splits are not cumulative."""
        with pytest.raises(ValueError, match="must be greater than previous"):
            parse_splits_string("50:58.44;100:28.27", 200, 12155)  # Second < first

    def test_split_exceeds_event_distance(self):
        """Error when split distance >= event distance."""
        with pytest.raises(ValueError, match="must be less than event distance"):
            parse_splits_string("50:28.27;100:58.44", 100, 5945)  # 100 == event distance

    def test_split_exceeds_final_time(self):
        """Error when split time >= final time."""
        with pytest.raises(ValueError, match="must be less than final time"):
            parse_splits_string("50:1:05.00", 100, 5945)  # 65.00 > 59.45

    def test_format_splits(self):
        """Format splits back to string."""
        from swimcuttimes.models.swim_time import Split

        splits = [
            Split(distance=50, time_centiseconds=2827),
            Split(distance=100, time_centiseconds=5844),
        ]
        result = format_splits(splits)
        assert result == "50:28.27;100:58.44"

    def test_format_empty_splits(self):
        """Format empty splits returns empty string."""
        assert format_splits([]) == ""


class TestRosterValidation:
    """Tests for roster validation."""

    @pytest.fixture
    def service(self):
        """Create ImportService with mock DAOs to avoid DB connection."""
        from unittest.mock import MagicMock
        return ImportService(
            swimmer_dao=MagicMock(),
            meet_dao=MagicMock(),
            team_dao=MagicMock(),
            event_dao=MagicMock(),
            swim_time_dao=MagicMock(),
        )

    def test_valid_roster_row(self, service):
        """Valid roster row passes validation."""
        rows = [
            RosterRow(
                first_name="Emily",
                last_name="Johnson",
                date_of_birth=date(2011, 3, 15),
                gender="F",
                usa_swimming_id="123456789",
                row_number=2,
            )
        ]

        result = service.validate_roster(rows)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_first_name(self, service):
        """Error for missing first name."""
        rows = [
            RosterRow(
                first_name="",
                last_name="Johnson",
                date_of_birth=date(2011, 3, 15),
                gender="F",
                row_number=2,
            )
        ]

        result = service.validate_roster(rows)
        assert not result.valid
        assert any("first_name" in e.field for e in result.errors)

    def test_future_birth_date(self, service):
        """Error for future birth date."""
        rows = [
            RosterRow(
                first_name="Emily",
                last_name="Johnson",
                date_of_birth=date(2030, 1, 1),
                gender="F",
                row_number=2,
            )
        ]

        result = service.validate_roster(rows)
        assert not result.valid
        assert any("future" in e.message.lower() for e in result.errors)

    def test_unusual_age_warning(self, service):
        """Warning for unusual age."""
        rows = [
            RosterRow(
                first_name="Emily",
                last_name="Johnson",
                date_of_birth=date(1980, 1, 1),  # ~44 years old
                gender="F",
                row_number=2,
            )
        ]

        result = service.validate_roster(rows)
        # Still valid (warning doesn't invalidate)
        assert result.valid
        assert len(result.warnings) > 0
        assert any("outside typical range" in w.message for w in result.warnings)

    def test_duplicate_swimmer_warning(self, service):
        """Warning for duplicate swimmer."""
        rows = [
            RosterRow(
                first_name="Emily",
                last_name="Johnson",
                date_of_birth=date(2011, 3, 15),
                gender="F",
                row_number=2,
            ),
            RosterRow(
                first_name="emily",  # Same name, different case
                last_name="JOHNSON",
                date_of_birth=date(2011, 3, 15),
                gender="F",
                row_number=3,
            ),
        ]

        result = service.validate_roster(rows)
        assert result.valid
        assert len(result.warnings) > 0
        assert any("Duplicate" in w.message for w in result.warnings)


class TestMeetsValidation:
    """Tests for meets validation."""

    @pytest.fixture
    def service(self):
        """Create ImportService with mock DAOs to avoid DB connection."""
        from unittest.mock import MagicMock

        return ImportService(
            swimmer_dao=MagicMock(),
            meet_dao=MagicMock(),
            team_dao=MagicMock(),
            event_dao=MagicMock(),
            swim_time_dao=MagicMock(),
        )

    def test_valid_meet_row(self, service):
        """Valid meet row passes validation."""
        rows = [
            MeetRow(
                name="Summer Championship",
                location="Harvard Pool",
                city="Boston",
                state="MA",
                start_date=date(2024, 7, 15),
                end_date=date(2024, 7, 17),
                course="lcm",
                sanctioning_body="NE Swimming",
                meet_type="championship",
                row_number=2,
            )
        ]

        result = service.validate_meets(rows)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_required_fields(self, service):
        """Error for missing required fields."""
        rows = [
            MeetRow(
                name="",  # Missing
                location="Pool",
                city="Boston",
                start_date=date(2024, 7, 15),
                course="scy",
                sanctioning_body="",  # Missing
                meet_type="invitational",
                row_number=2,
            )
        ]

        result = service.validate_meets(rows)
        assert not result.valid
        assert any("name" in e.field for e in result.errors)
        assert any("sanctioning_body" in e.field for e in result.errors)

    def test_end_before_start(self, service):
        """Error when end date is before start date."""
        rows = [
            MeetRow(
                name="Summer Championship",
                location="Harvard Pool",
                city="Boston",
                start_date=date(2024, 7, 17),
                end_date=date(2024, 7, 15),  # Before start
                course="lcm",
                sanctioning_body="NE Swimming",
                meet_type="championship",
                row_number=2,
            )
        ]

        result = service.validate_meets(rows)
        assert not result.valid
        assert any("end_date" in e.field for e in result.errors)


class TestTimesValidation:
    """Tests for times validation."""

    @pytest.fixture
    def service(self):
        """Create ImportService with mock DAOs to avoid DB connection."""
        from unittest.mock import MagicMock

        return ImportService(
            swimmer_dao=MagicMock(),
            meet_dao=MagicMock(),
            team_dao=MagicMock(),
            event_dao=MagicMock(),
            swim_time_dao=MagicMock(),
        )

    def test_valid_time_row(self, service):
        """Valid time row passes validation."""
        rows = [
            TimeRow(
                swimmer_first_name="Emily",
                swimmer_last_name="Johnson",
                distance=100,
                stroke="free",
                course="scy",
                meet_name="Summer Championship",
                time="59.45",
                swim_date=date(2024, 7, 15),
                team_name="Bluefish SC",
                row_number=2,
            )
        ]

        result = service.validate_times(rows)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_swimmer_identifier(self, service):
        """Error when no swimmer identifier."""
        rows = [
            TimeRow(
                # No swimmer_first_name, swimmer_last_name, or usa_swimming_id
                distance=100,
                stroke="free",
                course="scy",
                meet_name="Summer Championship",
                time="59.45",
                swim_date=date(2024, 7, 15),
                team_name="Bluefish SC",
                row_number=2,
            )
        ]

        result = service.validate_times(rows)
        assert not result.valid
        assert any("swimmer" in e.field for e in result.errors)

    def test_invalid_time_format(self, service):
        """Error for invalid time format."""
        rows = [
            TimeRow(
                swimmer_first_name="Emily",
                swimmer_last_name="Johnson",
                distance=100,
                stroke="free",
                course="scy",
                meet_name="Summer Championship",
                time="invalid",  # Invalid
                swim_date=date(2024, 7, 15),
                team_name="Bluefish SC",
                row_number=2,
            )
        ]

        result = service.validate_times(rows)
        assert not result.valid
        assert any("time" in e.field for e in result.errors)

    def test_valid_splits(self, service):
        """Valid splits pass validation."""
        rows = [
            TimeRow(
                swimmer_first_name="Emily",
                swimmer_last_name="Johnson",
                distance=200,
                stroke="free",
                course="scy",
                meet_name="Summer Championship",
                time="2:01.55",
                splits="50:28.27;100:58.44;150:1:29.19",
                swim_date=date(2024, 7, 15),
                team_name="Bluefish SC",
                row_number=2,
            )
        ]

        result = service.validate_times(rows)
        assert result.valid
        assert len(result.errors) == 0

    def test_invalid_splits_exceeds_final_time(self, service):
        """Error when split time exceeds final time."""
        rows = [
            TimeRow(
                swimmer_first_name="Emily",
                swimmer_last_name="Johnson",
                distance=100,
                stroke="free",
                course="scy",
                meet_name="Summer Championship",
                time="59.45",
                splits="50:1:05.00",  # Split exceeds final time
                swim_date=date(2024, 7, 15),
                team_name="Bluefish SC",
                row_number=2,
            )
        ]

        result = service.validate_times(rows)
        assert not result.valid
        assert any("splits" in e.field for e in result.errors)

    def test_cross_validation_with_roster(self, service):
        """Warning when swimmer not in roster."""
        roster = [
            RosterRow(
                first_name="Emily",
                last_name="Johnson",
                date_of_birth=date(2011, 3, 15),
                gender="F",
                row_number=2,
            )
        ]

        times = [
            TimeRow(
                swimmer_first_name="Unknown",
                swimmer_last_name="Person",
                distance=100,
                stroke="free",
                course="scy",
                meet_name="Summer Championship",
                time="59.45",
                swim_date=date(2024, 7, 15),
                team_name="Bluefish SC",
                row_number=2,
            )
        ]

        result = service.validate_times(times, roster=roster)
        # Still valid (warning doesn't invalidate)
        assert result.valid
        assert len(result.warnings) > 0
        assert any("not found in roster" in w.message for w in result.warnings)

    def test_cross_validation_with_meets(self, service):
        """Warning when meet not in meets list."""
        meets = [
            MeetRow(
                name="Summer Championship",
                location="Harvard Pool",
                city="Boston",
                start_date=date(2024, 7, 15),
                course="lcm",
                sanctioning_body="NE Swimming",
                meet_type="championship",
                row_number=2,
            )
        ]

        times = [
            TimeRow(
                swimmer_first_name="Emily",
                swimmer_last_name="Johnson",
                distance=100,
                stroke="free",
                course="scy",
                meet_name="Unknown Meet",  # Not in meets
                time="59.45",
                swim_date=date(2024, 7, 15),
                team_name="Bluefish SC",
                row_number=2,
            )
        ]

        result = service.validate_times(times, meets=meets)
        # Still valid (warning doesn't invalidate)
        assert result.valid
        assert len(result.warnings) > 0
        assert any("not found in meets" in w.message for w in result.warnings)
