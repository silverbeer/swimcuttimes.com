#!/usr/bin/env python3
"""CLI tool for testing DAO layer directly."""

from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load environment variables before importing DAOs
load_dotenv()

from swimcuttimes.dao import EventDAO, TimeStandardDAO  # noqa: E402
from swimcuttimes.models import Course, Gender, Stroke  # noqa: E402

app = typer.Typer(help="DAO testing CLI", no_args_is_help=True)
console = Console()

# Sub-apps for grouping commands
time_standards_app = typer.Typer(help="Time standard queries", no_args_is_help=True)
events_app = typer.Typer(help="Event queries", no_args_is_help=True)

app.add_typer(time_standards_app, name="ts")
app.add_typer(events_app, name="events")


def stroke_callback(value: str | None) -> Stroke | None:
    """Convert stroke string to enum."""
    if value is None:
        return None

    # Map short names to full names
    shortcuts = {
        "FREE": "freestyle",
        "BACK": "backstroke",
        "BREAST": "breaststroke",
        "FLY": "butterfly",
        "IM": "im",
    }

    val = value.upper()
    if val in shortcuts:
        return Stroke(shortcuts[val])

    try:
        return Stroke(value.lower())
    except ValueError:
        valid = "free, back, breast, fly, im (or full names)"
        raise typer.BadParameter(f"Invalid stroke. Valid: {valid}") from None


def course_callback(value: str | None) -> Course | None:
    """Convert course string to enum."""
    if value is None:
        return None
    try:
        return Course(value.lower())
    except ValueError:
        raise typer.BadParameter("Invalid course. Valid: scy, scm, lcm") from None


def gender_callback(value: str | None) -> Gender | None:
    """Convert gender string to enum."""
    if value is None:
        return None
    try:
        return Gender(value.upper())
    except ValueError:
        raise typer.BadParameter("Invalid gender. Valid: M, F") from None


def _group_time_standards(results: list) -> dict:
    """Group time standards by event/gender/age for side-by-side display."""
    grouped: dict[tuple, dict[str, str]] = {}

    for ts in results:
        key = (
            ts.event.distance,
            ts.event.stroke.value,
            ts.event.course.value,
            ts.gender.value,
            ts.age_group or "Open",
            ts.standard_name,
            ts.sanctioning_body,
        )
        if key not in grouped:
            grouped[key] = {"cut_time": "-", "cut_off": "-"}

        if "cut off" in ts.cut_level.lower():
            grouped[key]["cut_off"] = ts.time_formatted
        else:
            grouped[key]["cut_time"] = ts.time_formatted

    return grouped


@time_standards_app.command("search")
def ts_search(
    stroke: Annotated[
        str | None, typer.Option("--stroke", "-s", help="Stroke (free, back, breast, fly, im)")
    ] = None,
    distance: Annotated[
        int | None, typer.Option("--distance", "-d", help="Distance in yards/meters")
    ] = None,
    course: Annotated[
        str | None, typer.Option("--course", "-c", help="Course (scy, scm, lcm)")
    ] = None,
    gender: Annotated[
        str | None, typer.Option("--gender", "-g", help="Gender (M, F)")
    ] = None,
    age_group: Annotated[
        str | None, typer.Option("--age", "-a", help="Age group (e.g., 11-12, 15-18)")
    ] = None,
    sanctioning_body: Annotated[
        str | None, typer.Option("--body", "-b", help="Sanctioning body")
    ] = None,
    standard_name: Annotated[
        str | None, typer.Option("--name", "-n", help="Standard name")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 100,
):
    """Search time standards with filters."""
    dao = TimeStandardDAO()

    results = dao.search(
        stroke=stroke_callback(stroke),
        distance=distance,
        course=course_callback(course),
        gender=gender_callback(gender),
        age_group=age_group,
        sanctioning_body=sanctioning_body,
        standard_name=standard_name,
        limit=limit,
    )

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    grouped = _group_time_standards(results)

    table = Table(title=f"Time Standards ({len(grouped)} events)")
    table.add_column("Event", style="cyan")
    table.add_column("Gender", style="magenta", justify="center")
    table.add_column("Age", justify="center")
    table.add_column("Standard", style="green")
    table.add_column("Cut Time", style="bold yellow", justify="right")
    table.add_column("Cut Off", style="yellow", justify="right")

    for key, times in grouped.items():
        dist, stroke_val, course_val, gender_val, age, standard, _body = key
        event_str = f"{dist} {stroke_val} {course_val}"
        table.add_row(
            event_str,
            gender_val,
            age,
            standard,
            times["cut_time"],
            times["cut_off"],
        )

    console.print(table)


@time_standards_app.command("list")
def ts_list(
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 100,
):
    """List time standards (no filters)."""
    dao = TimeStandardDAO()
    results = dao.search(limit=limit)

    if not results:
        console.print("[yellow]No time standards found.[/yellow]")
        return

    grouped = _group_time_standards(results)

    table = Table(title=f"Time Standards ({len(grouped)} events)")
    table.add_column("Event", style="cyan")
    table.add_column("Gender", style="magenta", justify="center")
    table.add_column("Age", justify="center")
    table.add_column("Standard", style="green")
    table.add_column("Cut Time", style="bold yellow", justify="right")
    table.add_column("Cut Off", style="yellow", justify="right")

    for key, times in grouped.items():
        dist, stroke_val, course_val, gender_val, age, standard, _body = key
        event_str = f"{dist} {stroke_val} {course_val}"
        table.add_row(
            event_str,
            gender_val,
            age,
            standard,
            times["cut_time"],
            times["cut_off"],
        )

    console.print(table)


@time_standards_app.command("by-body")
def ts_by_body(
    body: Annotated[str, typer.Argument(help="Sanctioning body name")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 200,
):
    """Find time standards by sanctioning body."""
    dao = TimeStandardDAO()
    results = dao.find_by_sanctioning_body(body)[:limit]

    if not results:
        console.print(f"[yellow]No results for '{body}'[/yellow]")
        return

    grouped = _group_time_standards(results)

    table = Table(title=f"Time Standards for {body} ({len(grouped)} events)")
    table.add_column("Event", style="cyan")
    table.add_column("Gender", style="magenta", justify="center")
    table.add_column("Age", justify="center")
    table.add_column("Standard", style="green")
    table.add_column("Cut Time", style="bold yellow", justify="right")
    table.add_column("Cut Off", style="yellow", justify="right")

    for key, times in grouped.items():
        dist, stroke_val, course_val, gender_val, age, standard, _body = key
        event_str = f"{dist} {stroke_val} {course_val}"
        table.add_row(
            event_str,
            gender_val,
            age,
            standard,
            times["cut_time"],
            times["cut_off"],
        )

    console.print(table)


@events_app.command("list")
def events_list(
    stroke: Annotated[
        str | None, typer.Option("--stroke", "-s", help="Filter by stroke")
    ] = None,
    course: Annotated[
        str | None, typer.Option("--course", "-c", help="Filter by course")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results")] = 50,
):
    """List events."""
    dao = EventDAO()

    stroke_enum = stroke_callback(stroke)
    course_enum = course_callback(course)

    if stroke_enum and course_enum:
        results = dao.find_by_stroke_and_course(stroke_enum, course_enum)[:limit]
    elif stroke_enum:
        results = dao.find_by_stroke(stroke_enum)[:limit]
    elif course_enum:
        results = dao.find_by_course(course_enum)[:limit]
    else:
        results = dao.get_all()[:limit]

    if not results:
        console.print("[yellow]No events found.[/yellow]")
        return

    table = Table(title=f"Events ({len(results)} results)")
    table.add_column("ID", style="dim")
    table.add_column("Distance", justify="right", style="cyan")
    table.add_column("Stroke", style="magenta")
    table.add_column("Course", style="green")

    for event in results:
        table.add_row(
            str(event.id)[:8] + "..." if event.id else "-",
            str(event.distance),
            event.stroke.value,
            event.course.value,
        )

    console.print(table)


@events_app.command("count")
def events_count():
    """Count events by stroke and course."""
    dao = EventDAO()
    all_events = dao.get_all()

    # Count by stroke
    stroke_counts: dict[str, int] = {}
    course_counts: dict[str, int] = {}

    for event in all_events:
        stroke_counts[event.stroke.value] = stroke_counts.get(event.stroke.value, 0) + 1
        course_counts[event.course.value] = course_counts.get(event.course.value, 0) + 1

    table = Table(title=f"Event Summary ({len(all_events)} total)")

    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="yellow")

    table.add_section()
    for stroke, count in sorted(stroke_counts.items()):
        table.add_row(f"Stroke: {stroke}", str(count))

    table.add_section()
    for course, count in sorted(course_counts.items()):
        table.add_row(f"Course: {course}", str(count))

    console.print(table)


if __name__ == "__main__":
    app()
