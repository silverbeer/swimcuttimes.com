"""Utilities for parsing event descriptions and swim times."""

import re

from swimcuttimes.models.event import Course, Stroke
from swimcuttimes.models.swim_time import Split


# Stroke name aliases for flexible parsing
STROKE_ALIASES: dict[str, Stroke] = {
    # Freestyle
    "free": Stroke.FREESTYLE,
    "freestyle": Stroke.FREESTYLE,
    "fr": Stroke.FREESTYLE,
    # Backstroke
    "back": Stroke.BACKSTROKE,
    "backstroke": Stroke.BACKSTROKE,
    "bk": Stroke.BACKSTROKE,
    # Breaststroke
    "breast": Stroke.BREASTSTROKE,
    "breaststroke": Stroke.BREASTSTROKE,
    "br": Stroke.BREASTSTROKE,
    # Butterfly
    "fly": Stroke.BUTTERFLY,
    "butterfly": Stroke.BUTTERFLY,
    "fl": Stroke.BUTTERFLY,
    # Individual Medley
    "im": Stroke.IM,
    "medley": Stroke.IM,
}

# Course aliases
COURSE_ALIASES: dict[str, Course] = {
    "scy": Course.SCY,
    "yards": Course.SCY,
    "y": Course.SCY,
    "scm": Course.SCM,
    "lcm": Course.LCM,
    "meters": Course.LCM,  # Default meters to LCM
    "m": Course.LCM,
}


def parse_event_string(
    event_str: str,
    default_course: Course | None = None,
) -> tuple[int, Stroke, Course]:
    """Parse an event string into distance, stroke, and course.

    Supports formats:
    - "100 Free" (requires default_course)
    - "100 Free SCY"
    - "100 Freestyle SCY"
    - "200 IM LCM"

    Args:
        event_str: Event description string
        default_course: Default course if not specified in string

    Returns:
        Tuple of (distance, stroke, course)

    Raises:
        ValueError: If event string cannot be parsed
    """
    parts = event_str.lower().strip().split()

    if len(parts) < 2:
        raise ValueError(
            f"Invalid event format: '{event_str}'. "
            "Expected: '<distance> <stroke>' or '<distance> <stroke> <course>'"
        )

    # Parse distance (first part)
    try:
        distance = int(parts[0])
    except ValueError as e:
        raise ValueError(f"Invalid distance: '{parts[0]}'") from e

    # Validate distance is reasonable
    valid_distances = {25, 50, 100, 200, 400, 500, 800, 1000, 1500, 1650}
    if distance not in valid_distances:
        raise ValueError(
            f"Invalid distance: {distance}. "
            f"Valid distances: {sorted(valid_distances)}"
        )

    # Parse stroke (second part)
    stroke_str = parts[1]
    if stroke_str not in STROKE_ALIASES:
        valid_strokes = sorted(set(STROKE_ALIASES.keys()))
        raise ValueError(
            f"Invalid stroke: '{stroke_str}'. Valid strokes: {valid_strokes}"
        )
    stroke = STROKE_ALIASES[stroke_str]

    # Parse course (optional third part)
    if len(parts) >= 3:
        course_str = parts[2]
        if course_str not in COURSE_ALIASES:
            raise ValueError(
                f"Invalid course: '{course_str}'. Valid courses: scy, scm, lcm"
            )
        course = COURSE_ALIASES[course_str]
    elif default_course is not None:
        course = default_course
    else:
        raise ValueError(
            f"No course specified in '{event_str}' and no default course provided"
        )

    return distance, stroke, course


# Regex patterns for time parsing
# Matches MM:SS.cc or SS.cc
TIME_PATTERN_MINUTES = re.compile(r"^(\d+):(\d{1,2})\.(\d{1,2})$")
TIME_PATTERN_SECONDS = re.compile(r"^(\d+)\.(\d{1,2})$")


def parse_time_string(time_str: str) -> int:
    """Parse a time string into centiseconds.

    Supports formats:
    - "59.45" -> 5945 centiseconds
    - "1:23.45" -> 8345 centiseconds
    - "12:34.56" -> 75456 centiseconds

    Args:
        time_str: Time string in MM:SS.cc or SS.cc format

    Returns:
        Time in centiseconds

    Raises:
        ValueError: If time string cannot be parsed
    """
    time_str = time_str.strip()

    # Try MM:SS.cc format
    match = TIME_PATTERN_MINUTES.match(time_str)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        centiseconds_str = match.group(3)
        # Pad or truncate centiseconds to 2 digits
        if len(centiseconds_str) == 1:
            centiseconds = int(centiseconds_str) * 10
        else:
            centiseconds = int(centiseconds_str[:2])

        if seconds >= 60:
            raise ValueError(f"Invalid seconds value: {seconds} (must be < 60)")

        total = (minutes * 60 * 100) + (seconds * 100) + centiseconds
        return total

    # Try SS.cc format
    match = TIME_PATTERN_SECONDS.match(time_str)
    if match:
        seconds = int(match.group(1))
        centiseconds_str = match.group(2)
        # Pad or truncate centiseconds to 2 digits
        if len(centiseconds_str) == 1:
            centiseconds = int(centiseconds_str) * 10
        else:
            centiseconds = int(centiseconds_str[:2])

        total = (seconds * 100) + centiseconds
        return total

    raise ValueError(
        f"Invalid time format: '{time_str}'. Expected 'SS.cc' or 'MM:SS.cc'"
    )


def format_centiseconds(centiseconds: int) -> str:
    """Format centiseconds as a human-readable time string.

    Args:
        centiseconds: Time in centiseconds

    Returns:
        Formatted time string (SS.cc or MM:SS.cc)
    """
    total_seconds = centiseconds // 100
    cs = centiseconds % 100

    if total_seconds >= 60:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}.{cs:02d}"
    else:
        return f"{total_seconds}.{cs:02d}"


def parse_splits_string(
    splits_str: str,
    event_distance: int,
    final_time_centiseconds: int,
) -> list[Split]:
    """Parse a splits string into a list of Split objects.

    Format: "50:28.27;100:58.44;150:1:29.19"
    Each split is "distance:time" separated by semicolons.

    Args:
        splits_str: Splits string in "distance:time;distance:time" format
        event_distance: Total event distance for validation
        final_time_centiseconds: Final time for validation

    Returns:
        List of Split objects

    Raises:
        ValueError: If splits string is invalid or fails validation
    """
    if not splits_str or not splits_str.strip():
        return []

    splits: list[Split] = []
    parts = splits_str.strip().split(";")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Split on first colon only might not work for times like "100:1:23.45"
        # Need to find the distance:time boundary
        # Format is "distance:time" where time can be "SS.cc" or "MM:SS.cc"
        # So we look for pattern: digits followed by colon, then the time

        # Find the split between distance and time
        # Distance is always just digits before the first colon
        colon_idx = part.find(":")
        if colon_idx == -1:
            raise ValueError(f"Invalid split format: '{part}'. Expected 'distance:time'")

        distance_str = part[:colon_idx]
        time_str = part[colon_idx + 1 :]

        try:
            distance = int(distance_str)
        except ValueError as e:
            raise ValueError(f"Invalid split distance: '{distance_str}'") from e

        try:
            time_centiseconds = parse_time_string(time_str)
        except ValueError as e:
            raise ValueError(f"Invalid split time for {distance}m: {e}") from e

        splits.append(Split(distance=distance, time_centiseconds=time_centiseconds))

    # Validate splits
    _validate_splits(splits, event_distance, final_time_centiseconds)

    return splits


def _validate_splits(
    splits: list[Split],
    event_distance: int,
    final_time_centiseconds: int,
) -> None:
    """Validate parsed splits for consistency.

    Args:
        splits: List of Split objects
        event_distance: Total event distance
        final_time_centiseconds: Final time in centiseconds

    Raises:
        ValueError: If splits are invalid
    """
    if not splits:
        return

    # Sort splits by distance
    sorted_splits = sorted(splits, key=lambda s: s.distance)

    # Check that splits are cumulative (each time > previous)
    prev_time = 0
    for split in sorted_splits:
        if split.time_centiseconds <= prev_time:
            raise ValueError(
                f"Split at {split.distance} ({format_centiseconds(split.time_centiseconds)}) "
                f"must be greater than previous split ({format_centiseconds(prev_time)})"
            )
        prev_time = split.time_centiseconds

    # Check that max split distance < event distance
    max_split_distance = sorted_splits[-1].distance
    if max_split_distance >= event_distance:
        raise ValueError(
            f"Split distance {max_split_distance} must be less than event distance {event_distance}"
        )

    # Check that all split times < final time
    for split in sorted_splits:
        if split.time_centiseconds >= final_time_centiseconds:
            raise ValueError(
                f"Split at {split.distance} ({format_centiseconds(split.time_centiseconds)}) "
                f"must be less than final time ({format_centiseconds(final_time_centiseconds)})"
            )


def format_splits(splits: list[Split]) -> str:
    """Format a list of splits as a string.

    Args:
        splits: List of Split objects

    Returns:
        Formatted splits string like "50:28.27;100:58.44"
    """
    if not splits:
        return ""

    sorted_splits = sorted(splits, key=lambda s: s.distance)
    parts = [
        f"{s.distance}:{format_centiseconds(s.time_centiseconds)}" for s in sorted_splits
    ]
    return ";".join(parts)
