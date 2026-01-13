"""Event API endpoints.

Events are the standard swimming events (e.g., 100 Freestyle SCY).
These are typically seeded and read-only for regular users.
"""

from fastapi import APIRouter, HTTPException, Query, status

from swimcuttimes import get_logger
from swimcuttimes.api.auth import CurrentUser
from swimcuttimes.api.dependencies import EventDAODep
from swimcuttimes.models.event import Course, Event, Stroke

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


# =============================================================================
# READ - List (Authenticated users)
# =============================================================================


@router.get("", response_model=list[Event])
def list_events(
    user: CurrentUser,
    dao: EventDAODep,
    stroke: Stroke | None = Query(None, description="Filter by stroke"),
    distance: int | None = Query(None, description="Filter by distance"),
    course: Course | None = Query(None, description="Filter by course (scy/scm/lcm)"),
    limit: int = Query(100, ge=1, le=500),
) -> list[Event]:
    """List events with optional filters."""
    # If all three filters specified, return single match
    if stroke and distance and course:
        event = dao.find_by_stroke_distance_course(stroke, distance, course)
        return [event] if event else []

    # Otherwise filter by individual criteria
    if stroke:
        events = dao.find_by_stroke(stroke)
    elif course:
        events = dao.find_by_course(course)
    elif distance:
        events = dao.find_by_distance(distance)
    else:
        events = dao.get_all(limit=limit)

    return events[:limit]


# =============================================================================
# READ - Get by ID (Authenticated users)
# =============================================================================


@router.get("/{event_id}", response_model=Event)
def get_event(
    event_id: str,
    user: CurrentUser,
    dao: EventDAODep,
) -> Event:
    """Get a specific event by ID."""
    result = dao.get_by_id(event_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return result


# =============================================================================
# LOOKUP - Find by description (Authenticated users)
# =============================================================================


@router.get("/lookup/{description}", response_model=Event)
def lookup_event(
    description: str,
    user: CurrentUser,
    dao: EventDAODep,
) -> Event:
    """Look up an event by description like '100 free scy' or '200 back lcm'.

    Format: <distance> <stroke> <course>
    - distance: 50, 100, 200, 500, 1000, 1650, etc.
    - stroke: free/freestyle, back/backstroke, breast/breaststroke, fly/butterfly, im
    - course: scy, scm, lcm
    """
    try:
        distance, stroke, course = _parse_event_description(description)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    event = dao.find_by_stroke_distance_course(stroke, distance, course)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event not found: {distance} {stroke.value} {course.value}",
        )
    return event


def _parse_event_description(description: str) -> tuple[int, Stroke, Course]:
    """Parse an event description like '100 free scy'.

    Args:
        description: Event description string

    Returns:
        Tuple of (distance, stroke, course)

    Raises:
        ValueError: If description cannot be parsed
    """
    parts = description.lower().strip().split()
    if len(parts) != 3:
        raise ValueError(
            "Event must be: <distance> <stroke> <course> (e.g., '100 free scy')"
        )

    # Parse distance
    try:
        distance = int(parts[0])
    except ValueError as e:
        raise ValueError(f"Invalid distance: {parts[0]}") from e

    # Parse stroke
    stroke_map = {
        "free": Stroke.FREESTYLE,
        "freestyle": Stroke.FREESTYLE,
        "back": Stroke.BACKSTROKE,
        "backstroke": Stroke.BACKSTROKE,
        "breast": Stroke.BREASTSTROKE,
        "breaststroke": Stroke.BREASTSTROKE,
        "fly": Stroke.BUTTERFLY,
        "butterfly": Stroke.BUTTERFLY,
        "im": Stroke.IM,
    }
    stroke_str = parts[1]
    if stroke_str not in stroke_map:
        valid = ", ".join(stroke_map.keys())
        raise ValueError(f"Invalid stroke: {stroke_str}. Valid: {valid}")
    stroke = stroke_map[stroke_str]

    # Parse course
    course_map = {
        "scy": Course.SCY,
        "scm": Course.SCM,
        "lcm": Course.LCM,
    }
    course_str = parts[2]
    if course_str not in course_map:
        raise ValueError(f"Invalid course: {course_str}. Valid: scy, scm, lcm")
    course = course_map[course_str]

    return distance, stroke, course
