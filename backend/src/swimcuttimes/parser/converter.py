"""Convert parsed time standard data to domain models."""

from datetime import date

from swimcuttimes.models.event import Event
from swimcuttimes.models.time_standard import TimeStandard, parse_time_to_centiseconds
from swimcuttimes.parser.schemas import ParsedTimeEntry, ParsedTimeStandardSheet


def convert_entry_to_time_standard(
    entry: ParsedTimeEntry,
    sheet: ParsedTimeStandardSheet,
) -> TimeStandard:
    """Convert a single parsed entry to a TimeStandard model.

    Args:
        entry: Parsed time entry from the image
        sheet: Parent sheet with metadata

    Returns:
        TimeStandard model ready for database storage
    """
    event = Event(
        stroke=entry.event_stroke,
        distance=entry.event_distance,
        course=entry.course,
    )

    # Parse qualifying dates if available
    qualifying_start = None
    qualifying_end = None

    # Try to parse dates (these come as strings like "January 1, 2024")
    # For now, leave as None - could add date parsing later
    # TODO: Add robust date parsing for qualifying periods

    return TimeStandard(
        event=event,
        gender=entry.gender,
        age_group=sheet.age_group,
        standard_name=sheet.standard_name,
        cut_level=entry.cut_level,
        sanctioning_body=sheet.sanctioning_body,
        time_centiseconds=parse_time_to_centiseconds(entry.time_str),
        qualifying_start=qualifying_start,
        qualifying_end=qualifying_end,
        effective_year=sheet.effective_year,
    )


def convert_sheet_to_time_standards(sheet: ParsedTimeStandardSheet) -> list[TimeStandard]:
    """Convert all entries from a parsed sheet to TimeStandard models.

    Args:
        sheet: Parsed time standard sheet

    Returns:
        List of TimeStandard models
    """
    return [convert_entry_to_time_standard(entry, sheet) for entry in sheet.entries]


def parse_qualifying_date(date_str: str | None) -> date | None:
    """Parse a qualifying date string to a date object.

    Handles formats like:
    - "January 1, 2024"
    - "01/01/2024"
    - "2024-01-01"

    Args:
        date_str: Date string or None

    Returns:
        Parsed date or None if parsing fails
    """
    if not date_str:
        return None

    # Common date formats to try
    from datetime import datetime

    formats = [
        "%B %d, %Y",  # January 1, 2024
        "%b %d, %Y",  # Jan 1, 2024
        "%m/%d/%Y",  # 01/01/2024
        "%Y-%m-%d",  # 2024-01-01
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    return None
