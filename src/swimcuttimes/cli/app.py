"""Swim Cut Times CLI application.

Usage:
    swimcuttimes auth login
    swimcuttimes auth logout
    swimcuttimes auth status
    swimcuttimes ts list
    swimcuttimes ts import <image>
    swimcuttimes invite create coach user@example.com
"""

import os
from pathlib import Path

import typer
from dotenv import load_dotenv

# Load .env file for API keys, etc.
load_dotenv()
from rich.console import Console
from rich.table import Table

from swimcuttimes.cli import auth as cli_auth

console = Console()
app = typer.Typer(
    name="swimcuttimes",
    help="Swim cut times tracking CLI",
    no_args_is_help=True,
)


# =============================================================================
# AUTH COMMANDS
# =============================================================================

auth_app = typer.Typer(help="Authentication commands", no_args_is_help=True)
app.add_typer(auth_app, name="auth")


DEFAULT_DOMAIN = "swimcuttimes.com"


@auth_app.command("login")
def auth_login(
    username: str = typer.Option(None, "--user", "-u", help="Username or email"),
    password: str = typer.Option(None, "--password", "-p", help="Password"),
):
    """Login to Swim Cut Times."""
    if not username:
        username = typer.prompt("Username")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    # Auto-append domain if no @ in username
    email = username if "@" in username else f"{username}@{DEFAULT_DOMAIN}"

    try:
        with console.status("Logging in..."):
            creds = cli_auth.login(email, password)

        console.print(f"[green]Logged in as {creds.display_name or creds.email}[/green]")
        console.print(f"Role: {creds.role}")

    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@auth_app.command("logout")
def auth_logout():
    """Logout and clear stored credentials."""
    cli_auth.logout()
    console.print("[green]Logged out[/green]")


@auth_app.command("status")
def auth_status():
    """Show current authentication status."""
    creds = cli_auth.load_credentials()

    if not creds:
        console.print("[yellow]Not logged in[/yellow]")
        console.print("Run: swimcuttimes auth login")
        raise typer.Exit(1)

    table = Table(title="Current Session")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Email", creds.email)
    table.add_row("Display Name", creds.display_name or "-")
    table.add_row("Role", creds.role)
    table.add_row("User ID", creds.user_id)

    console.print(table)


@auth_app.command("whoami")
def auth_whoami():
    """Get current user info from API."""
    try:
        creds = cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Fetching user info..."):
        user = cli_auth.get_current_user()

    if not user:
        console.print("[red]Failed to fetch user info. Token may be expired.[/red]")
        console.print("Try: swimcuttimes auth login")
        raise typer.Exit(1)

    table = Table(title="Current User")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("ID", user.get("id", "-"))
    table.add_row("Email", creds.email)
    table.add_row("Display Name", user.get("display_name", "-"))
    table.add_row("Role", user.get("role", "-"))

    console.print(table)


# =============================================================================
# TIME STANDARDS COMMANDS
# =============================================================================

ts_app = typer.Typer(help="Time standards commands", no_args_is_help=True)
app.add_typer(ts_app, name="ts")


def _parse_image_to_json(image_path: Path) -> Path:
    """Parse image and save to JSON file. Returns JSON path."""
    from swimcuttimes.parser import TimeStandardParser

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set[/red]")
        console.print("[dim]Add to .env: ANTHROPIC_API_KEY=sk-ant-...[/dim]")
        raise typer.Exit(1)

    console.print(f"[cyan]Parsing image:[/cyan] {image_path}")
    with console.status("Analyzing image with Claude Vision..."):
        try:
            parser = TimeStandardParser()
            sheet = parser.parse_image_file(image_path)
        except Exception as e:
            console.print(f"[red]Failed to parse image: {e}[/red]")
            raise typer.Exit(1) from None

    # Show what was parsed
    console.print()
    console.print("[green]Parsed successfully![/green]")
    console.print(f"  Title: {sheet.title}")
    console.print(f"  Standard: {sheet.standard_name}")
    console.print(f"  Sanctioning Body: {sheet.sanctioning_body}")
    console.print(f"  Age Group: {sheet.age_group or 'Open'}")
    console.print(f"  Year: {sheet.effective_year}")
    console.print(f"  Entries: {len(sheet.entries)}")

    # Save to JSON file alongside the image
    import json

    json_path = image_path.with_suffix(".json")
    json_data = {
        "title": sheet.title,
        "sanctioning_body": sheet.sanctioning_body,
        "standard_name": sheet.standard_name,
        "effective_year": sheet.effective_year,
        "age_group": sheet.age_group,
        "qualifying_period_start": sheet.qualifying_period_start,
        "qualifying_period_end": sheet.qualifying_period_end,
        "entries": [
            {
                "event_distance": e.event_distance,
                "event_stroke": e.event_stroke.value,
                "course": e.course.value,
                "gender": e.gender.value,
                "time_str": e.time_str,
                "cut_level": e.cut_level,
            }
            for e in sheet.entries
        ],
    }
    json_path.write_text(json.dumps(json_data, indent=2))

    console.print()
    console.print(f"[green]Saved to:[/green] {json_path}")
    return json_path


def _load_json_to_db(json_path: Path) -> None:
    """Load time standards from JSON file into database."""
    import json

    from swimcuttimes.parser import convert_sheet_to_time_standards
    from swimcuttimes.parser.schemas import ParsedTimeEntry, ParsedTimeStandardSheet
    from swimcuttimes.models import Course, Gender, Stroke

    # Load JSON
    data = json.loads(json_path.read_text())

    # Convert back to ParsedTimeStandardSheet
    entries = [
        ParsedTimeEntry(
            event_distance=e["event_distance"],
            event_stroke=Stroke(e["event_stroke"]),
            course=Course(e["course"]),
            gender=Gender(e["gender"]),
            time_str=e["time_str"],
            cut_level=e["cut_level"],
        )
        for e in data["entries"]
    ]

    sheet = ParsedTimeStandardSheet(
        title=data.get("title", ""),
        sanctioning_body=data.get("sanctioning_body", ""),
        standard_name=data.get("standard_name", ""),
        effective_year=data.get("effective_year", 2025),
        age_group=data.get("age_group"),
        qualifying_period_start=data.get("qualifying_period_start"),
        qualifying_period_end=data.get("qualifying_period_end"),
        entries=entries,
    )

    # Convert to time standards
    standards = convert_sheet_to_time_standards(sheet)

    # Pivot for preview - group by event/gender to show both cut levels
    pivoted = _pivot_standards_models(standards)

    # Preview table
    console.print()
    preview_table = _make_ts_table(f"Preview ({len(pivoted)} events)", pivoted[:15])
    console.print(preview_table)

    if len(pivoted) > 15:
        console.print(f"[dim]... and {len(pivoted) - 15} more events[/dim]")

    console.print()

    # Confirm import
    if not typer.confirm(f"Import {len(standards)} time standards?"):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)

    # Import via API
    imported = 0
    errors = 0
    error_messages: list[str] = []

    with console.status("Importing time standards...") as status:
        for i, ts in enumerate(standards):
            status.update(f"Importing time standards... ({i + 1}/{len(standards)})")

            response = cli_auth.api_request(
                "POST",
                "/api/v1/time-standards",
                json_data={
                    "event": {
                        "stroke": ts.event.stroke.value,
                        "distance": ts.event.distance,
                        "course": ts.event.course.value,
                    },
                    "gender": ts.gender.value,
                    "age_group": ts.age_group,
                    "standard_name": ts.standard_name,
                    "cut_level": ts.cut_level,
                    "sanctioning_body": ts.sanctioning_body,
                    "time_centiseconds": ts.time_centiseconds,
                    "effective_year": ts.effective_year,
                },
            )

            if response.status_code in (200, 201):
                imported += 1
            else:
                errors += 1
                if len(error_messages) < 5:
                    event_str = f"{ts.event.distance} {ts.event.stroke.value} {ts.event.course.value.upper()}"
                    try:
                        detail = response.json().get("detail", response.text)
                    except Exception:
                        detail = response.text
                    error_messages.append(f"{event_str}: {response.status_code} - {detail}")

    console.print()
    console.print(f"[green]Imported {imported} time standards[/green]")
    if errors:
        console.print(f"[red]Errors: {errors}[/red]")
        for msg in error_messages:
            console.print(f"  [dim]{msg}[/dim]")
        if errors > len(error_messages):
            console.print(f"  [dim]... and {errors - len(error_messages)} more[/dim]")


@ts_app.command("parse")
def ts_parse(
    image_path: Path = typer.Argument(..., help="Path to time standards image"),
):
    """Parse a time standards image and save as JSON for review."""
    if not image_path.exists():
        console.print(f"[red]File not found: {image_path}[/red]")
        raise typer.Exit(1)

    _parse_image_to_json(image_path)
    console.print()
    console.print("[dim]Review/edit the JSON, then run: swimcuttimes ts load <json>[/dim]")


@ts_app.command("load")
def ts_load(
    json_path: Path = typer.Argument(..., help="Path to time standards JSON file"),
):
    """Load time standards from a JSON file into the database."""
    if not json_path.exists():
        console.print(f"[red]File not found: {json_path}[/red]")
        raise typer.Exit(1)

    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    console.print(f"[cyan]Loading:[/cyan] {json_path}")
    _load_json_to_db(json_path)


@ts_app.command("import")
def ts_import(
    image_path: Path = typer.Argument(..., help="Path to time standards image"),
):
    """Parse image and import to database in one step."""
    if not image_path.exists():
        console.print(f"[red]File not found: {image_path}[/red]")
        raise typer.Exit(1)

    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Step 1: Parse to JSON
    json_path = _parse_image_to_json(image_path)

    # Step 2: Load to database
    _load_json_to_db(json_path)


def _pivot_standards_models(standards: list) -> list[dict]:
    """Pivot TimeStandard models to group Cut Off Time and Cut Time into single rows."""
    from collections import defaultdict

    grouped: dict[tuple, dict] = defaultdict(lambda: {
        "event": None,
        "gender": None,
        "age_group": None,
        "cut_off_time": "-",
        "cut_time": "-",
    })

    for ts in standards:
        key = (
            ts.event.distance,
            ts.event.stroke.value,
            ts.event.course.value,
            ts.gender.value,
            ts.age_group,
        )

        row = grouped[key]
        row["event"] = ts.event
        row["gender"] = ts.gender.value
        row["age_group"] = ts.age_group

        cut_level = (ts.cut_level or "").lower()
        time_str = ts.time_formatted

        if "cut off" in cut_level:
            row["cut_off_time"] = time_str
        elif "cut" in cut_level:
            row["cut_time"] = time_str

    return list(grouped.values())


def _pivot_time_standards(standards: list[dict]) -> list[dict]:
    """Pivot time standards to group Cut Off Time and Cut Time into single rows.

    Args:
        standards: List of time standard dicts from API

    Returns:
        List of pivoted rows with cut_off_time and cut_time columns
    """
    from collections import defaultdict

    # Group by event + gender + age_group
    grouped: dict[tuple, dict] = defaultdict(lambda: {
        "event": None,
        "gender": None,
        "age_group": None,
        "cut_off_time": "-",
        "cut_time": "-",
    })

    for ts in standards:
        event = ts.get("event", {})
        key = (
            event.get("distance"),
            event.get("stroke"),
            event.get("course"),
            ts.get("gender"),
            ts.get("age_group"),
        )

        row = grouped[key]
        row["event"] = event
        row["gender"] = ts.get("gender")
        row["age_group"] = ts.get("age_group")

        cut_level = ts.get("cut_level", "").lower()
        time_str = ts.get("time_formatted", "-")

        if "cut off" in cut_level:
            row["cut_off_time"] = time_str
        elif "cut" in cut_level:
            row["cut_time"] = time_str

    return list(grouped.values())


def _make_ts_table(title: str, rows: list[dict]) -> Table:
    """Create a time standards table with Cut Off Time and Cut Time columns."""
    table = Table(title=title)
    table.add_column("Event", style="cyan")
    table.add_column("Course", style="magenta")
    table.add_column("Gender")
    table.add_column("Age Group")
    table.add_column("Cut Off Time", style="yellow")
    table.add_column("Cut Time", style="green")

    for row in rows:
        event = row.get("event", {})
        if isinstance(event, dict):
            dist = event.get("distance", "?")
            stroke = event.get("stroke", "?")
            course = event.get("course", "?").upper()
        else:
            # Handle model objects
            dist = getattr(event, "distance", "?")
            stroke = getattr(event, "stroke", "?")
            if hasattr(stroke, "value"):
                stroke = stroke.value
            course = getattr(event, "course", "?")
            if hasattr(course, "value"):
                course = course.value.upper()
            else:
                course = str(course).upper()

        event_str = f"{dist} {stroke}"

        table.add_row(
            event_str,
            course,
            str(row.get("gender", "-")).upper(),
            row.get("age_group") or "Open",
            row.get("cut_off_time", "-"),
            row.get("cut_time", "-"),
        )

    return table


@ts_app.command("list")
def ts_list(
    gender: str = typer.Option(None, "--gender", "-g", help="Filter by gender (M/F)"),
    stroke: str = typer.Option(None, "--stroke", "-s", help="Filter by stroke (freestyle/backstroke/breaststroke/butterfly/im)"),
    course: str = typer.Option(None, "--course", "-c", help="Filter by course (scy/scm/lcm)"),
    distance: int = typer.Option(None, "--distance", "-d", help="Filter by distance (50/100/200/500/etc)"),
    age_group: str = typer.Option(None, "--age", "-a", help="Filter by age group (e.g., 10-under, 11-12, 13-14, 15-18, Open)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
):
    """List time standards."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Build query params
    params = []
    if gender:
        params.append(f"gender={gender.upper()}")
    if stroke:
        params.append(f"stroke={stroke.lower()}")
    if course:
        params.append(f"course={course.lower()}")
    if distance:
        params.append(f"distance={distance}")
    if age_group:
        params.append(f"age_group={age_group}")
    params.append(f"limit={limit}")

    query = "&".join(params)
    path = f"/api/v1/time-standards?{query}"

    with console.status("Fetching time standards..."):
        response = cli_auth.api_request("GET", path)

    if response.status_code != 200:
        try:
            err = response.json()
            if isinstance(err.get("detail"), list):
                # Validation errors
                console.print()
                console.print("[bold red]❌ Validation Error[/bold red]")
                for e in err["detail"]:
                    field = e.get("loc", ["?"])[-1]
                    msg = e.get("msg", "Invalid value")
                    console.print(f"   [yellow]⚠️  {field}:[/yellow] {msg}")
                console.print()
            else:
                console.print(f"[red]❌ Error: {err.get('detail', response.text)}[/red]")
        except Exception:
            console.print(f"[red]❌ Error: {response.text}[/red]")
        raise typer.Exit(1)

    standards = response.json()
    pivoted = _pivot_time_standards(standards)

    table = _make_ts_table(f"Time Standards ({len(pivoted)} events)", pivoted)
    console.print(table)


# =============================================================================
# INVITE COMMANDS (Admin only)
# =============================================================================

invite_app = typer.Typer(help="Invitation management (admin only)", no_args_is_help=True)
app.add_typer(invite_app, name="invite")


@invite_app.command("create")
def invite_create(
    role: str = typer.Argument(..., help="Role to assign (admin/coach/swimmer/fan)"),
    email: str = typer.Argument(..., help="Email to invite"),
):
    """Create an invitation."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Validate role
    valid_roles = ["admin", "coach", "swimmer", "fan"]
    if role.lower() not in valid_roles:
        console.print(f"[red]Invalid role. Must be one of: {', '.join(valid_roles)}[/red]")
        raise typer.Exit(1)

    with console.status(f"Creating invitation for {email}..."):
        response = cli_auth.api_request(
            "POST",
            "/api/v1/auth/invitations",
            json_data={"email": email, "role": role.lower()},
        )

    if response.status_code == 403:
        console.print(f"[red]Permission denied: You cannot invite {role}s[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        console.print(f"[red]Pending invitation already exists for {email}[/red]")
        raise typer.Exit(1)

    if response.status_code != 201:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    invite = response.json()

    console.print("[green]Invitation created![/green]")
    console.print()
    console.print(f"Email: {invite['email']}")
    console.print(f"Role: {invite['role']}")
    console.print(f"Token: [bold]{invite['token']}[/bold]")
    console.print()
    console.print("[dim]Share this token with the user to sign up.[/dim]")


@invite_app.command("list")
def invite_list():
    """List sent invitations."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Fetching invitations..."):
        response = cli_auth.api_request("GET", "/api/v1/auth/invitations")

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    invites = response.json()

    if not invites:
        console.print("[yellow]No invitations found[/yellow]")
        return

    table = Table(title="Invitations")
    table.add_column("Email", style="cyan")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Token")

    for inv in invites:
        status_color = {
            "pending": "yellow",
            "accepted": "green",
            "expired": "dim",
            "revoked": "red",
        }.get(inv["status"], "white")

        table.add_row(
            inv["email"],
            inv["role"],
            f"[{status_color}]{inv['status']}[/{status_color}]",
            inv.get("token", "-")[:16] + "..." if inv.get("token") else "-",
        )

    console.print(table)


@invite_app.command("revoke")
def invite_revoke(
    invitation_id: str = typer.Argument(..., help="Invitation ID to revoke"),
):
    """Revoke a pending invitation."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Revoking invitation..."):
        response = cli_auth.api_request("DELETE", f"/api/v1/auth/invitations/{invitation_id}")

    if response.status_code == 404:
        console.print("[red]Invitation not found[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print("[green]Invitation revoked[/green]")


# =============================================================================
# USERS COMMANDS (Admin only)
# =============================================================================

users_app = typer.Typer(help="User management (admin only)", no_args_is_help=True)
app.add_typer(users_app, name="users")


@users_app.command("list")
def users_list():
    """List all users."""
    try:
        cli_auth.require_admin()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Fetching users..."):
        response = cli_auth.api_request("GET", "/api/v1/auth/users")

    if response.status_code == 403:
        console.print("[red]Admin access required[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    users = response.json()

    if not users:
        console.print("[yellow]No users found[/yellow]")
        return

    table = Table(title=f"Users ({len(users)})")
    table.add_column("ID", style="dim")
    table.add_column("Display Name", style="cyan")
    table.add_column("Role")

    for user in users:
        role_color = {
            "admin": "red",
            "coach": "blue",
            "swimmer": "green",
            "fan": "yellow",
        }.get(user["role"], "white")

        table.add_row(
            user["id"][:8] + "...",
            user.get("display_name", "-"),
            f"[{role_color}]{user['role']}[/{role_color}]",
        )

    console.print(table)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
