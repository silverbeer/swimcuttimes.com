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


def _resolve_invitation(identifier: str) -> dict:
    """Resolve an invitation by ID (partial UUID) or email.

    Args:
        identifier: Either a partial UUID (min 8 chars) or email address

    Returns:
        Invitation dict from API

    Raises:
        typer.Exit: If invitation not found or ambiguous
    """
    import re

    # Fetch all invitations
    response = cli_auth.api_request("GET", "/api/v1/auth/invitations")
    if response.status_code != 200:
        console.print(f"[red]Error fetching invitations: {response.text}[/red]")
        raise typer.Exit(1)

    invites = response.json()

    # Check if it looks like a UUID (hex chars, possibly with dashes)
    is_uuid_like = bool(re.match(r'^[0-9a-f-]+$', identifier.lower()))

    if is_uuid_like and len(identifier.replace('-', '')) >= 8:
        # Try partial UUID match
        matches = [i for i in invites if i["id"].startswith(identifier.lower())]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            console.print(f"[red]Ambiguous ID '{identifier}' matches {len(matches)} invitations:[/red]")
            for i in matches[:5]:
                console.print(f"  {i['id'][:8]}  {i['email']}")
            raise typer.Exit(1)

    # Try email match
    email_matches = [i for i in invites if i["email"].lower() == identifier.lower()]

    if len(email_matches) == 1:
        return email_matches[0]
    elif len(email_matches) > 1:
        # Multiple invites to same email (different statuses) - prefer pending
        pending = [i for i in email_matches if i["status"] == "pending"]
        if len(pending) == 1:
            return pending[0]
        console.print(f"[red]Multiple invitations for '{identifier}':[/red]")
        for i in email_matches[:5]:
            console.print(f"  {i['id'][:8]}  {i['status']}")
        raise typer.Exit(1)

    # No match found
    console.print(f"[red]Invitation not found: '{identifier}'[/red]")
    console.print("[dim]Use a partial UUID (min 8 chars) or email address[/dim]")
    raise typer.Exit(1)


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

    table = Table(title=f"Invitations ({len(invites)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Email", style="cyan", no_wrap=True)
    table.add_column("Role", no_wrap=True)
    table.add_column("Status", no_wrap=True)

    for inv in invites:
        status_color = {
            "pending": "yellow",
            "accepted": "green",
            "expired": "dim",
            "revoked": "red",
        }.get(inv["status"], "white")

        table.add_row(
            inv["id"][:8],
            inv["email"],
            inv["role"],
            f"[{status_color}]{inv['status']}[/{status_color}]",
        )

    console.print(table)


@invite_app.command("revoke")
def invite_revoke(
    invite_ref: str = typer.Argument(..., help="Invitation ID (partial) or email"),
):
    """Revoke a pending invitation."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve invitation first
    with console.status("Finding invitation..."):
        invite = _resolve_invitation(invite_ref)

    if invite["status"] != "pending":
        console.print(f"[red]Cannot revoke invitation with status '{invite['status']}'[/red]")
        raise typer.Exit(1)

    with console.status("Revoking invitation..."):
        response = cli_auth.api_request("DELETE", f"/api/v1/auth/invitations/{invite['id']}")

    if response.status_code == 404:
        console.print("[red]Invitation not found[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Invitation to {invite['email']} revoked[/green]")


# =============================================================================
# TEAMS COMMANDS
# =============================================================================

teams_app = typer.Typer(help="Team management", no_args_is_help=True)
app.add_typer(teams_app, name="teams")


def _resolve_team(identifier: str) -> dict:
    """Resolve a team by ID (partial UUID) or name.

    Args:
        identifier: Either a partial UUID (min 8 chars) or exact team name

    Returns:
        Team dict from API

    Raises:
        typer.Exit: If team not found or ambiguous
    """
    import re

    # Check if it looks like a UUID (hex chars, possibly with dashes)
    is_uuid_like = bool(re.match(r'^[0-9a-f-]+$', identifier.lower()))

    if is_uuid_like and len(identifier.replace('-', '')) >= 8:
        # Try partial UUID match - fetch all teams and filter
        response = cli_auth.api_request("GET", "/api/v1/teams?limit=500")
        if response.status_code != 200:
            console.print(f"[red]Error fetching teams: {response.text}[/red]")
            raise typer.Exit(1)

        teams = response.json()
        matches = [t for t in teams if t["id"].startswith(identifier.lower())]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            console.print(f"[red]Ambiguous ID '{identifier}' matches {len(matches)} teams:[/red]")
            for t in matches[:5]:
                console.print(f"  {t['id'][:8]}  {t['name']}")
            raise typer.Exit(1)
        # Fall through to try name match

    # Try exact name match
    response = cli_auth.api_request("GET", f"/api/v1/teams?name={identifier}&limit=10")
    if response.status_code != 200:
        console.print(f"[red]Error searching teams: {response.text}[/red]")
        raise typer.Exit(1)

    teams = response.json()
    # Look for exact name match (API does partial match)
    exact_matches = [t for t in teams if t["name"].lower() == identifier.lower()]

    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        console.print(f"[red]Multiple teams match '{identifier}'[/red]")
        raise typer.Exit(1)

    # No match found
    console.print(f"[red]Team not found: '{identifier}'[/red]")
    console.print("[dim]Use a partial UUID (min 8 chars) or exact team name[/dim]")
    raise typer.Exit(1)


@teams_app.command("list")
def teams_list(
    name: str = typer.Option(None, "--name", "-n", help="Filter by name (partial match)"),
    team_type: str = typer.Option(
        None, "--type", "-t", help="Filter by type (club/high_school/college/national/olympic)"
    ),
    lsc: str = typer.Option(None, "--lsc", "-l", help="Filter by LSC code (e.g., NE, PV)"),
    state: str = typer.Option(None, "--state", "-s", help="Filter by state"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
):
    """List teams with optional filters."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Build query params
    params = []
    if name:
        params.append(f"name={name}")
    if team_type:
        params.append(f"team_type={team_type}")
    if lsc:
        params.append(f"lsc={lsc}")
    if state:
        params.append(f"state={state}")
    params.append(f"limit={limit}")

    query = "&".join(params)
    path = f"/api/v1/teams?{query}"

    with console.status("Fetching teams..."):
        response = cli_auth.api_request("GET", path)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    teams = response.json()

    if not teams:
        console.print("[yellow]No teams found[/yellow]")
        return

    table = Table(title=f"Teams ({len(teams)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", no_wrap=True)
    table.add_column("Body", no_wrap=True)
    table.add_column("LSC", no_wrap=True)

    for team in teams:
        team_type_val = team.get("team_type", "")
        type_color = {
            "club": "blue",
            "high_school": "green",
            "college": "magenta",
            "national": "yellow",
            "olympic": "red",
        }.get(team_type_val, "white")

        # Show relevant field based on team type
        extra = team.get("lsc") or team.get("division") or team.get("state") or "-"

        table.add_row(
            team["id"][:8],
            team["name"],
            f"[{type_color}]{team_type_val}[/{type_color}]",
            team.get("sanctioning_body", "-"),
            extra,
        )

    console.print(table)


@teams_app.command("get")
def teams_get(
    team_ref: str = typer.Argument(..., help="Team ID (partial) or name"),
):
    """Get details for a specific team."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Fetching team..."):
        team = _resolve_team(team_ref)

    table = Table(title="Team Details")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("ID", team["id"])
    table.add_row("Name", team["name"])
    table.add_row("Type", team["team_type"])
    table.add_row("Sanctioning Body", team.get("sanctioning_body", "-"))
    table.add_row("LSC", team.get("lsc") or "-")
    table.add_row("Division", team.get("division") or "-")
    table.add_row("State", team.get("state") or "-")
    table.add_row("Country", team.get("country") or "-")

    console.print(table)


@teams_app.command("create")
def teams_create(
    name: str = typer.Option(..., "--name", "-n", help="Team name"),
    team_type: str = typer.Option(
        ..., "--type", "-t", help="Team type (club/high_school/college/national/olympic)"
    ),
    sanctioning_body: str = typer.Option(
        ..., "--sanctioning-body", "-b", help="Sanctioning body (e.g., USA Swimming, NCAA)"
    ),
    lsc: str = typer.Option(None, "--lsc", "-l", help="LSC code (REQUIRED for club teams, e.g., NE, PV)"),
    division: str = typer.Option(None, "--division", "-d", help="Division for college teams"),
    state: str = typer.Option(None, "--state", "-s", help="State for high school teams"),
    country: str = typer.Option(None, "--country", "-c", help="Country for national/olympic teams"),
):
    """Create a new team (admin only)."""
    try:
        cli_auth.require_admin()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    payload = {
        "name": name,
        "team_type": team_type,
        "sanctioning_body": sanctioning_body,
    }
    if lsc:
        payload["lsc"] = lsc
    if division:
        payload["division"] = division
    if state:
        payload["state"] = state
    if country:
        payload["country"] = country

    with console.status("Creating team..."):
        response = cli_auth.api_request("POST", "/api/v1/teams", json_data=payload)

    if response.status_code == 400:
        err = response.json()
        console.print(f"[red]Validation error: {err.get('detail', response.text)}[/red]")
        raise typer.Exit(1)

    if response.status_code == 403:
        console.print("[red]Admin access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'Team name already exists')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 201:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    team = response.json()
    console.print("[green]Team created![/green]")
    console.print(f"ID: {team['id']}")
    console.print(f"Name: {team['name']}")


@teams_app.command("update")
def teams_update(
    team_ref: str = typer.Argument(..., help="Team ID (partial) or name"),
    name: str = typer.Option(None, "--name", "-n", help="New team name"),
    sanctioning_body: str = typer.Option(
        None, "--sanctioning-body", "-b", help="New sanctioning body"
    ),
    lsc: str = typer.Option(None, "--lsc", "-l", help="New LSC code"),
    division: str = typer.Option(None, "--division", "-d", help="New division"),
    state: str = typer.Option(None, "--state", "-s", help="New state"),
    country: str = typer.Option(None, "--country", "-c", help="New country"),
):
    """Update a team (admin only)."""
    try:
        cli_auth.require_admin()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve team first
    with console.status("Finding team..."):
        team = _resolve_team(team_ref)
    team_id = team["id"]

    payload = {}
    if name:
        payload["name"] = name
    if sanctioning_body:
        payload["sanctioning_body"] = sanctioning_body
    if lsc:
        payload["lsc"] = lsc
    if division:
        payload["division"] = division
    if state:
        payload["state"] = state
    if country:
        payload["country"] = country

    if not payload:
        console.print("[yellow]No updates provided[/yellow]")
        raise typer.Exit(1)

    with console.status("Updating team..."):
        response = cli_auth.api_request("PATCH", f"/api/v1/teams/{team_id}", json_data=payload)

    if response.status_code == 404:
        console.print("[red]Team not found[/red]")
        raise typer.Exit(1)

    if response.status_code == 400:
        err = response.json()
        console.print(f"[red]Validation error: {err.get('detail', response.text)}[/red]")
        raise typer.Exit(1)

    if response.status_code == 403:
        console.print("[red]Admin access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'Team name already exists')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    team = response.json()
    console.print("[green]Team updated![/green]")
    console.print(f"Name: {team['name']}")


@teams_app.command("delete")
def teams_delete(
    team_ref: str = typer.Argument(..., help="Team ID (partial) or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a team (admin only)."""
    try:
        cli_auth.require_admin()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve team first
    with console.status("Finding team..."):
        team = _resolve_team(team_ref)
    team_id = team["id"]

    if not force and not typer.confirm(f"Delete team '{team['name']}'?"):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)

    with console.status("Deleting team..."):
        response = cli_auth.api_request("DELETE", f"/api/v1/teams/{team_id}")

    if response.status_code == 403:
        console.print("[red]Admin access required[/red]")
        raise typer.Exit(1)

    if response.status_code != 204:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Team '{team['name']}' deleted[/green]")


# =============================================================================
# SWIMMERS COMMANDS
# =============================================================================

swimmers_app = typer.Typer(help="Swimmer management", no_args_is_help=True)
app.add_typer(swimmers_app, name="swimmers")


def _resolve_swimmer(identifier: str) -> dict:
    """Resolve a swimmer by ID (partial UUID), name, or USA Swimming ID.

    Args:
        identifier: Either a partial UUID (min 8 chars), name ("First Last"), or USA Swimming ID

    Returns:
        Swimmer dict from API

    Raises:
        typer.Exit: If swimmer not found or ambiguous
    """
    import re

    # Check if it looks like a UUID (hex chars, possibly with dashes)
    is_uuid_like = bool(re.match(r'^[0-9a-f-]+$', identifier.lower()))

    if is_uuid_like and len(identifier.replace('-', '')) >= 8:
        # Try partial UUID match - fetch all swimmers and filter
        response = cli_auth.api_request("GET", "/api/v1/swimmers?limit=500")
        if response.status_code != 200:
            console.print(f"[red]Error fetching swimmers: {response.text}[/red]")
            raise typer.Exit(1)

        swimmers = response.json()
        matches = [s for s in swimmers if s["id"].startswith(identifier.lower())]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            console.print(f"[red]Ambiguous ID '{identifier}' matches {len(matches)} swimmers:[/red]")
            for s in matches[:5]:
                console.print(f"  {s['id'][:8]}  {s['first_name']} {s['last_name']}")
            raise typer.Exit(1)
        # Fall through to try name match

    # Try name match (search API does partial match)
    response = cli_auth.api_request("GET", f"/api/v1/swimmers?name={identifier}&limit=10")
    if response.status_code != 200:
        console.print(f"[red]Error searching swimmers: {response.text}[/red]")
        raise typer.Exit(1)

    swimmers = response.json()

    # Look for exact name match (first last or last, first)
    name_lower = identifier.lower()
    exact_matches = []
    for s in swimmers:
        full_name = f"{s['first_name']} {s['last_name']}".lower()
        reverse_name = f"{s['last_name']}, {s['first_name']}".lower()
        last_name = s['last_name'].lower()
        if full_name == name_lower or reverse_name == name_lower or last_name == name_lower:
            exact_matches.append(s)

    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        console.print(f"[red]Multiple swimmers match '{identifier}':[/red]")
        for s in exact_matches[:5]:
            console.print(f"  {s['id'][:8]}  {s['first_name']} {s['last_name']}")
        raise typer.Exit(1)

    # Try USA Swimming ID match
    response = cli_auth.api_request("GET", "/api/v1/swimmers?limit=500")
    if response.status_code == 200:
        swimmers = response.json()
        usa_matches = [s for s in swimmers if s.get("usa_swimming_id") == identifier]
        if len(usa_matches) == 1:
            return usa_matches[0]

    # No match found
    console.print(f"[red]Swimmer not found: '{identifier}'[/red]")
    console.print("[dim]Use a partial UUID (min 8 chars), name, or USA Swimming ID[/dim]")
    raise typer.Exit(1)


@swimmers_app.command("list")
def swimmers_list(
    name: str = typer.Option(None, "--name", "-n", help="Filter by name"),
    gender: str = typer.Option(None, "--gender", "-g", help="Filter by gender (M/F)"),
    min_age: int = typer.Option(None, "--min-age", help="Minimum age"),
    max_age: int = typer.Option(None, "--max-age", help="Maximum age"),
    team: str = typer.Option(None, "--team", "-t", help="Filter by team (not yet implemented)"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
):
    """List swimmers with optional filters."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Build query params
    params = []
    if name:
        params.append(f"name={name}")
    if gender:
        params.append(f"gender={gender.upper()}")
    if min_age:
        params.append(f"min_age={min_age}")
    if max_age:
        params.append(f"max_age={max_age}")
    params.append(f"limit={limit}")

    query = "&".join(params)
    path = f"/api/v1/swimmers?{query}"

    with console.status("Fetching swimmers..."):
        response = cli_auth.api_request("GET", path)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    swimmers = response.json()

    if not swimmers:
        console.print("[yellow]No swimmers found[/yellow]")
        return

    table = Table(title=f"Swimmers ({len(swimmers)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Gender", no_wrap=True)
    table.add_column("Age", no_wrap=True)
    table.add_column("Age Group", no_wrap=True)

    for swimmer in swimmers:
        gender_color = "blue" if swimmer.get("gender") == "M" else "magenta"
        table.add_row(
            swimmer["id"][:8],
            f"{swimmer['first_name']} {swimmer['last_name']}",
            f"[{gender_color}]{swimmer.get('gender', '-')}[/{gender_color}]",
            str(swimmer.get("age", "-")),
            swimmer.get("age_group", "-"),
        )

    console.print(table)


@swimmers_app.command("get")
def swimmers_get(
    swimmer_ref: str = typer.Argument(..., help="Swimmer ID (partial), name, or USA Swimming ID"),
):
    """Get details for a specific swimmer."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Fetching swimmer..."):
        swimmer = _resolve_swimmer(swimmer_ref)

    table = Table(title="Swimmer Details")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("ID", swimmer["id"])
    table.add_row("Name", f"{swimmer['first_name']} {swimmer['last_name']}")
    table.add_row("Gender", swimmer.get("gender", "-"))
    table.add_row("Date of Birth", swimmer.get("date_of_birth", "-"))
    table.add_row("Age", str(swimmer.get("age", "-")))
    table.add_row("Age Group", swimmer.get("age_group", "-"))
    table.add_row("USA Swimming ID", swimmer.get("usa_swimming_id") or "-")
    table.add_row("SwimCloud URL", swimmer.get("swimcloud_url") or "-")

    console.print(table)


@swimmers_app.command("create")
def swimmers_create(
    first_name: str = typer.Option(..., "--first", "-f", help="First name"),
    last_name: str = typer.Option(..., "--last", "-l", help="Last name"),
    birth_date: str = typer.Option(..., "--birth", "-b", help="Date of birth (YYYY-MM-DD)"),
    gender: str = typer.Option(..., "--gender", "-g", help="Gender (M/F)"),
    usa_swimming_id: str = typer.Option(None, "--usa-id", help="USA Swimming ID"),
    swimcloud_url: str = typer.Option(None, "--swimcloud", help="SwimCloud URL"),
):
    """Create a new swimmer (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": birth_date,
        "gender": gender.upper(),
    }
    if usa_swimming_id:
        payload["usa_swimming_id"] = usa_swimming_id
    if swimcloud_url:
        payload["swimcloud_url"] = swimcloud_url

    with console.status("Creating swimmer..."):
        response = cli_auth.api_request("POST", "/api/v1/swimmers", json_data=payload)

    if response.status_code == 400:
        err = response.json()
        console.print(f"[red]Validation error: {err.get('detail', response.text)}[/red]")
        raise typer.Exit(1)

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'Swimmer already exists')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 201:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    swimmer = response.json()
    console.print("[green]Swimmer created![/green]")
    console.print(f"ID: {swimmer['id'][:8]}")
    console.print(f"Name: {swimmer['first_name']} {swimmer['last_name']}")


@swimmers_app.command("update")
def swimmers_update(
    swimmer_ref: str = typer.Argument(..., help="Swimmer ID (partial), name, or USA Swimming ID"),
    first_name: str = typer.Option(None, "--first", "-f", help="New first name"),
    last_name: str = typer.Option(None, "--last", "-l", help="New last name"),
    birth_date: str = typer.Option(None, "--birth", "-b", help="New date of birth (YYYY-MM-DD)"),
    gender: str = typer.Option(None, "--gender", "-g", help="New gender (M/F)"),
    usa_swimming_id: str = typer.Option(None, "--usa-id", help="New USA Swimming ID"),
    swimcloud_url: str = typer.Option(None, "--swimcloud", help="New SwimCloud URL"),
):
    """Update a swimmer (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve swimmer first
    with console.status("Finding swimmer..."):
        swimmer = _resolve_swimmer(swimmer_ref)
    swimmer_id = swimmer["id"]

    payload = {}
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    if birth_date:
        payload["date_of_birth"] = birth_date
    if gender:
        payload["gender"] = gender.upper()
    if usa_swimming_id:
        payload["usa_swimming_id"] = usa_swimming_id
    if swimcloud_url:
        payload["swimcloud_url"] = swimcloud_url

    if not payload:
        console.print("[yellow]No updates provided[/yellow]")
        raise typer.Exit(1)

    with console.status("Updating swimmer..."):
        response = cli_auth.api_request("PATCH", f"/api/v1/swimmers/{swimmer_id}", json_data=payload)

    if response.status_code == 404:
        console.print("[red]Swimmer not found[/red]")
        raise typer.Exit(1)

    if response.status_code == 400:
        err = response.json()
        console.print(f"[red]Validation error: {err.get('detail', response.text)}[/red]")
        raise typer.Exit(1)

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'USA Swimming ID already exists')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    swimmer = response.json()
    console.print("[green]Swimmer updated![/green]")
    console.print(f"Name: {swimmer['first_name']} {swimmer['last_name']}")


@swimmers_app.command("delete")
def swimmers_delete(
    swimmer_ref: str = typer.Argument(..., help="Swimmer ID (partial), name, or USA Swimming ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a swimmer (admin only)."""
    try:
        cli_auth.require_admin()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve swimmer first
    with console.status("Finding swimmer..."):
        swimmer = _resolve_swimmer(swimmer_ref)
    swimmer_id = swimmer["id"]
    swimmer_name = f"{swimmer['first_name']} {swimmer['last_name']}"

    if not force and not typer.confirm(f"Delete swimmer '{swimmer_name}'?"):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)

    with console.status("Deleting swimmer..."):
        response = cli_auth.api_request("DELETE", f"/api/v1/swimmers/{swimmer_id}")

    if response.status_code == 403:
        console.print("[red]Admin access required[/red]")
        raise typer.Exit(1)

    if response.status_code != 204:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Swimmer '{swimmer_name}' deleted[/green]")


@swimmers_app.command("teams")
def swimmers_teams(
    swimmer_ref: str = typer.Argument(..., help="Swimmer ID (partial), name, or USA Swimming ID"),
    all_history: bool = typer.Option(False, "--all", "-a", help="Include historical memberships"),
):
    """List teams a swimmer belongs to."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve swimmer first
    with console.status("Finding swimmer..."):
        swimmer = _resolve_swimmer(swimmer_ref)
    swimmer_id = swimmer["id"]
    swimmer_name = f"{swimmer['first_name']} {swimmer['last_name']}"

    current_only = "false" if all_history else "true"
    path = f"/api/v1/swimmers/{swimmer_id}/teams?current_only={current_only}"

    with console.status("Fetching teams..."):
        response = cli_auth.api_request("GET", path)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    teams = response.json()

    if not teams:
        console.print(f"[yellow]{swimmer_name} is not on any teams[/yellow]")
        return

    table = Table(title=f"Teams for {swimmer_name}")
    table.add_column("Team", style="cyan", no_wrap=True)
    table.add_column("Start Date", no_wrap=True)
    table.add_column("End Date", no_wrap=True)
    table.add_column("Status", no_wrap=True)

    for team in teams:
        status = "[green]Current[/green]" if team.get("is_current") else "[dim]Past[/dim]"
        table.add_row(
            team.get("team_name", "-"),
            team.get("start_date", "-"),
            team.get("end_date") or "-",
            status,
        )

    console.print(table)


@swimmers_app.command("assign")
def swimmers_assign(
    swimmer_ref: str = typer.Argument(..., help="Swimmer ID (partial), name, or USA Swimming ID"),
    team_ref: str = typer.Argument(..., help="Team ID (partial) or name"),
    start_date: str = typer.Option(None, "--start", "-s", help="Start date (YYYY-MM-DD, default: today)"),
):
    """Assign a swimmer to a team (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve swimmer and team
    with console.status("Finding swimmer and team..."):
        swimmer = _resolve_swimmer(swimmer_ref)
        team = _resolve_team(team_ref)

    swimmer_id = swimmer["id"]
    team_id = team["id"]
    swimmer_name = f"{swimmer['first_name']} {swimmer['last_name']}"
    team_name = team["name"]

    payload = {"team_id": team_id}
    if start_date:
        payload["start_date"] = start_date

    with console.status("Assigning swimmer to team..."):
        response = cli_auth.api_request("POST", f"/api/v1/swimmers/{swimmer_id}/teams", json_data=payload)

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 404:
        console.print("[red]Swimmer or team not found[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'Already a member of this team')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 201:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]{swimmer_name} assigned to {team_name}[/green]")


@swimmers_app.command("unassign")
def swimmers_unassign(
    swimmer_ref: str = typer.Argument(..., help="Swimmer ID (partial), name, or USA Swimming ID"),
    team_ref: str = typer.Argument(..., help="Team ID (partial) or name"),
    end_date: str = typer.Option(None, "--end", "-e", help="End date (YYYY-MM-DD, default: today)"),
):
    """End a swimmer's team membership (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve swimmer and team
    with console.status("Finding swimmer and team..."):
        swimmer = _resolve_swimmer(swimmer_ref)
        team = _resolve_team(team_ref)

    swimmer_id = swimmer["id"]
    team_id = team["id"]
    swimmer_name = f"{swimmer['first_name']} {swimmer['last_name']}"
    team_name = team["name"]

    path = f"/api/v1/swimmers/{swimmer_id}/teams/{team_id}"
    if end_date:
        path += f"?end_date={end_date}"

    with console.status("Ending team membership..."):
        response = cli_auth.api_request("DELETE", path)

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 404:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'Not a current member of this team')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]{swimmer_name} removed from {team_name}[/green]")


# =============================================================================
# MEETS COMMANDS
# =============================================================================

meets_app = typer.Typer(help="Meet management", no_args_is_help=True)
app.add_typer(meets_app, name="meets")


def _resolve_meet(identifier: str) -> dict:
    """Resolve a meet by ID (partial UUID) or name.

    Args:
        identifier: Either a partial UUID (min 8 chars) or exact meet name

    Returns:
        Meet dict from API

    Raises:
        typer.Exit: If meet not found or ambiguous
    """
    import re

    # Check if it looks like a UUID (hex chars, possibly with dashes)
    is_uuid_like = bool(re.match(r'^[0-9a-f-]+$', identifier.lower()))

    if is_uuid_like and len(identifier.replace('-', '')) >= 8:
        # Try partial UUID match - fetch all meets and filter
        response = cli_auth.api_request("GET", "/api/v1/meets?limit=500")
        if response.status_code != 200:
            console.print(f"[red]Error fetching meets: {response.text}[/red]")
            raise typer.Exit(1)

        meets = response.json()
        matches = [m for m in meets if m["id"].startswith(identifier.lower())]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            console.print(f"[red]Ambiguous ID '{identifier}' matches {len(matches)} meets:[/red]")
            for m in matches[:5]:
                console.print(f"  {m['id'][:8]}  {m['name']}")
            raise typer.Exit(1)
        # Fall through to try name match

    # Try exact name match
    response = cli_auth.api_request("GET", f"/api/v1/meets?name={identifier}&limit=10")
    if response.status_code != 200:
        console.print(f"[red]Error searching meets: {response.text}[/red]")
        raise typer.Exit(1)

    meets = response.json()
    # Look for exact name match (API does partial match)
    exact_matches = [m for m in meets if m["name"].lower() == identifier.lower()]

    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        console.print(f"[red]Multiple meets match '{identifier}'[/red]")
        raise typer.Exit(1)

    # Try partial name match if no exact match
    if len(meets) == 1:
        return meets[0]

    # No match found
    console.print(f"[red]Meet not found: '{identifier}'[/red]")
    console.print("[dim]Use a partial UUID (min 8 chars) or meet name[/dim]")
    raise typer.Exit(1)


@meets_app.command("list")
def meets_list(
    name: str = typer.Option(None, "--name", "-n", help="Filter by name (partial match)"),
    course: str = typer.Option(None, "--course", "-c", help="Filter by course (scy/scm/lcm)"),
    meet_type: str = typer.Option(
        None, "--type", "-t", help="Filter by type (championship/invitational/dual/time_trial)"
    ),
    after: str = typer.Option(None, "--after", help="Only meets starting after this date (YYYY-MM-DD)"),
    before: str = typer.Option(None, "--before", help="Only meets starting before this date (YYYY-MM-DD)"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
):
    """List meets with optional filters."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Build query params
    params = []
    if name:
        params.append(f"name={name}")
    if course:
        params.append(f"course={course.lower()}")
    if meet_type:
        params.append(f"meet_type={meet_type}")
    if after:
        params.append(f"start_after={after}")
    if before:
        params.append(f"start_before={before}")
    params.append(f"limit={limit}")

    query = "&".join(params)
    path = f"/api/v1/meets?{query}"

    with console.status("Fetching meets..."):
        response = cli_auth.api_request("GET", path)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    meets = response.json()

    if not meets:
        console.print("[yellow]No meets found[/yellow]")
        return

    table = Table(title=f"Meets ({len(meets)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Date", no_wrap=True)
    table.add_column("Course", style="magenta", no_wrap=True)
    table.add_column("Type", no_wrap=True)

    for meet in meets:
        type_color = {
            "championship": "green",
            "invitational": "blue",
            "dual": "yellow",
            "time_trial": "dim",
        }.get(meet.get("meet_type", ""), "white")

        table.add_row(
            meet["id"][:8],
            meet["name"],
            meet.get("start_date", "-"),
            meet.get("course", "-").upper(),
            f"[{type_color}]{meet.get('meet_type', '-')}[/{type_color}]",
        )

    console.print(table)


@meets_app.command("get")
def meets_get(
    meet_ref: str = typer.Argument(..., help="Meet ID (partial) or name"),
):
    """Get details for a specific meet."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Fetching meet..."):
        meet = _resolve_meet(meet_ref)

    table = Table(title="Meet Details")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("ID", meet["id"])
    table.add_row("Name", meet["name"])
    table.add_row("Location", meet.get("location", "-"))
    table.add_row("City", meet.get("city", "-"))
    table.add_row("State", meet.get("state") or "-")
    table.add_row("Start Date", meet.get("start_date", "-"))
    table.add_row("End Date", meet.get("end_date") or "-")
    table.add_row("Course", meet.get("course", "-").upper())
    table.add_row("Lanes", str(meet.get("lanes", "-")))
    table.add_row("Indoor", "Yes" if meet.get("indoor") else "No")
    table.add_row("Meet Type", meet.get("meet_type", "-"))
    table.add_row("Sanctioning Body", meet.get("sanctioning_body", "-"))

    console.print(table)


@meets_app.command("create")
def meets_create(
    name: str = typer.Option(..., "--name", "-n", help="Meet name"),
    location: str = typer.Option(..., "--location", "-l", help="Venue name"),
    city: str = typer.Option(..., "--city", help="City"),
    course: str = typer.Option(..., "--course", "-c", help="Course (scy/scm/lcm)"),
    start_date: str = typer.Option(..., "--date", "-d", help="Start date (YYYY-MM-DD)"),
    meet_type: str = typer.Option(
        ..., "--type", "-t", help="Meet type (championship/invitational/dual/time_trial)"
    ),
    sanctioning_body: str = typer.Option(
        ..., "--sanctioning-body", "-b", help="Sanctioning body (e.g., USA Swimming, MIAA)"
    ),
    state: str = typer.Option(None, "--state", "-s", help="State"),
    lanes: int = typer.Option(6, "--lanes", help="Number of lanes (6/8/10)"),
    indoor: bool = typer.Option(True, "--indoor/--outdoor", help="Indoor or outdoor"),
):
    """Create a new meet (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    payload = {
        "name": name,
        "location": location,
        "city": city,
        "course": course.lower(),
        "start_date": start_date,
        "meet_type": meet_type,
        "sanctioning_body": sanctioning_body,
        "lanes": lanes,
        "indoor": indoor,
    }
    if state:
        payload["state"] = state

    with console.status("Creating meet..."):
        response = cli_auth.api_request("POST", "/api/v1/meets", json_data=payload)

    if response.status_code == 400:
        err = response.json()
        console.print(f"[red]Validation error: {err.get('detail', response.text)}[/red]")
        raise typer.Exit(1)

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'Meet name already exists')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 201:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    meet = response.json()
    console.print("[green]Meet created![/green]")
    console.print(f"ID: {meet['id'][:8]}")
    console.print(f"Name: {meet['name']}")


@meets_app.command("update")
def meets_update(
    meet_ref: str = typer.Argument(..., help="Meet ID (partial) or name"),
    name: str = typer.Option(None, "--name", "-n", help="New meet name"),
    location: str = typer.Option(None, "--location", "-l", help="New venue name"),
    city: str = typer.Option(None, "--city", help="New city"),
    state: str = typer.Option(None, "--state", "-s", help="New state"),
    course: str = typer.Option(None, "--course", "-c", help="New course (scy/scm/lcm)"),
    lanes: int = typer.Option(None, "--lanes", help="New number of lanes"),
):
    """Update a meet (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve meet first
    with console.status("Finding meet..."):
        meet = _resolve_meet(meet_ref)
    meet_id = meet["id"]

    payload = {}
    if name:
        payload["name"] = name
    if location:
        payload["location"] = location
    if city:
        payload["city"] = city
    if state:
        payload["state"] = state
    if course:
        payload["course"] = course.lower()
    if lanes:
        payload["lanes"] = lanes

    if not payload:
        console.print("[yellow]No updates provided[/yellow]")
        raise typer.Exit(1)

    with console.status("Updating meet..."):
        response = cli_auth.api_request("PATCH", f"/api/v1/meets/{meet_id}", json_data=payload)

    if response.status_code == 404:
        console.print("[red]Meet not found[/red]")
        raise typer.Exit(1)

    if response.status_code == 400:
        err = response.json()
        console.print(f"[red]Validation error: {err.get('detail', response.text)}[/red]")
        raise typer.Exit(1)

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    meet = response.json()
    console.print("[green]Meet updated![/green]")
    console.print(f"Name: {meet['name']}")


@meets_app.command("delete")
def meets_delete(
    meet_ref: str = typer.Argument(..., help="Meet ID (partial) or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a meet (admin only)."""
    try:
        cli_auth.require_admin()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve meet first
    with console.status("Finding meet..."):
        meet = _resolve_meet(meet_ref)
    meet_id = meet["id"]

    if not force and not typer.confirm(f"Delete meet '{meet['name']}'?"):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)

    with console.status("Deleting meet..."):
        response = cli_auth.api_request("DELETE", f"/api/v1/meets/{meet_id}")

    if response.status_code == 403:
        console.print("[red]Admin access required[/red]")
        raise typer.Exit(1)

    if response.status_code != 204:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Meet '{meet['name']}' deleted[/green]")


@meets_app.command("teams")
def meets_teams(
    meet_ref: str = typer.Argument(..., help="Meet ID (partial) or name"),
):
    """List teams participating in a meet."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve meet first
    with console.status("Finding meet..."):
        meet = _resolve_meet(meet_ref)
    meet_id = meet["id"]
    meet_name = meet["name"]

    with console.status("Fetching teams..."):
        response = cli_auth.api_request("GET", f"/api/v1/meets/{meet_id}/teams")

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    teams = response.json()

    if not teams:
        console.print(f"[yellow]No teams registered for '{meet_name}'[/yellow]")
        return

    table = Table(title=f"Teams in {meet_name}")
    table.add_column("Team", style="cyan", no_wrap=True)
    table.add_column("Host", no_wrap=True)

    for team in teams:
        host_status = "[green]Yes[/green]" if team.get("is_host") else "-"
        table.add_row(
            team.get("team_name", "-"),
            host_status,
        )

    console.print(table)


@meets_app.command("add-team")
def meets_add_team(
    meet_ref: str = typer.Argument(..., help="Meet ID (partial) or name"),
    team_ref: str = typer.Argument(..., help="Team ID (partial) or name"),
    host: bool = typer.Option(False, "--host", "-h", help="Mark as host team"),
):
    """Add a team to a meet (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve meet and team
    with console.status("Finding meet and team..."):
        meet = _resolve_meet(meet_ref)
        team = _resolve_team(team_ref)

    meet_id = meet["id"]
    team_id = team["id"]
    meet_name = meet["name"]
    team_name = team["name"]

    payload = {"team_id": team_id, "is_host": host}

    with console.status("Adding team to meet..."):
        response = cli_auth.api_request("POST", f"/api/v1/meets/{meet_id}/teams", json_data=payload)

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 404:
        console.print("[red]Meet or team not found[/red]")
        raise typer.Exit(1)

    if response.status_code == 409:
        err = response.json()
        console.print(f"[red]{err.get('detail', 'Team already in meet')}[/red]")
        raise typer.Exit(1)

    if response.status_code != 201:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    host_str = " as host" if host else ""
    console.print(f"[green]{team_name} added to {meet_name}{host_str}[/green]")


@meets_app.command("remove-team")
def meets_remove_team(
    meet_ref: str = typer.Argument(..., help="Meet ID (partial) or name"),
    team_ref: str = typer.Argument(..., help="Team ID (partial) or name"),
):
    """Remove a team from a meet (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve meet and team
    with console.status("Finding meet and team..."):
        meet = _resolve_meet(meet_ref)
        team = _resolve_team(team_ref)

    meet_id = meet["id"]
    team_id = team["id"]
    meet_name = meet["name"]
    team_name = team["name"]

    with console.status("Removing team from meet..."):
        response = cli_auth.api_request("DELETE", f"/api/v1/meets/{meet_id}/teams/{team_id}")

    if response.status_code == 403:
        console.print("[red]Admin or coach access required[/red]")
        raise typer.Exit(1)

    if response.status_code == 404:
        console.print("[red]Team is not in this meet[/red]")
        raise typer.Exit(1)

    if response.status_code != 204:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]{team_name} removed from {meet_name}[/green]")


# =============================================================================
# TIMES COMMANDS
# =============================================================================

times_app = typer.Typer(help="Swim time management", no_args_is_help=True)
app.add_typer(times_app, name="times")


def _parse_event(event_str: str) -> tuple[int, str, str]:
    """Parse an event string like '100 free scy' into (distance, stroke, course).

    Args:
        event_str: Event string in format "DISTANCE STROKE COURSE"
                   e.g., "100 free scy", "200 back lcm", "500 fly"

    Returns:
        Tuple of (distance, stroke, course)

    Raises:
        ValueError: If event string is invalid
    """
    parts = event_str.lower().split()
    if len(parts) < 2:
        raise ValueError("Event must be in format 'DISTANCE STROKE [COURSE]', e.g., '100 free scy'")

    # Parse distance
    try:
        distance = int(parts[0])
    except ValueError:
        raise ValueError(f"Invalid distance: {parts[0]}") from None

    # Parse stroke
    stroke_map = {
        "free": "freestyle",
        "freestyle": "freestyle",
        "back": "backstroke",
        "backstroke": "backstroke",
        "breast": "breaststroke",
        "breaststroke": "breaststroke",
        "fly": "butterfly",
        "butterfly": "butterfly",
        "im": "im",
    }
    stroke = stroke_map.get(parts[1])
    if not stroke:
        raise ValueError(f"Invalid stroke: {parts[1]}. Use free/back/breast/fly/im")

    # Parse course (optional, default to scy)
    course = "scy"
    if len(parts) >= 3:
        course = parts[2].lower()
        if course not in ("scy", "scm", "lcm"):
            raise ValueError(f"Invalid course: {parts[2]}. Use scy/scm/lcm")

    return distance, stroke, course


def _find_event_id(distance: int, stroke: str, course: str) -> str | None:
    """Find the event ID for a given distance/stroke/course combination.

    Args:
        distance: Event distance
        stroke: Event stroke
        course: Pool course

    Returns:
        Event ID or None if not found
    """
    # The events table is reference data - we need to look it up
    # For now, we'll create the event on the fly via swim_times API
    # which handles event resolution
    return None


@times_app.command("list")
def times_list(
    swimmer: str = typer.Option(None, "--swimmer", "-s", help="Filter by swimmer (ID or name)"),
    meet: str = typer.Option(None, "--meet", "-m", help="Filter by meet (ID or name)"),
    event: str = typer.Option(None, "--event", "-e", help="Filter by event (e.g., '100 free scy')"),
    team: str = typer.Option(None, "--team", "-t", help="Filter by team (ID or name)"),
    limit: int = typer.Option(50, "--limit", help="Max results"),
):
    """List swim times with optional filters."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Build query params
    params = []

    # Resolve swimmer ID if provided
    if swimmer:
        with console.status("Finding swimmer..."):
            swimmer_data = _resolve_swimmer(swimmer)
        params.append(f"swimmer_id={swimmer_data['id']}")

    # Resolve meet ID if provided
    if meet:
        with console.status("Finding meet..."):
            meet_data = _resolve_meet(meet)
        params.append(f"meet_id={meet_data['id']}")

    # Resolve team ID if provided
    if team:
        with console.status("Finding team..."):
            team_data = _resolve_team(team)
        params.append(f"team_id={team_data['id']}")

    params.append(f"limit={limit}")

    query = "&".join(params)
    path = f"/api/v1/swim-times?{query}"

    with console.status("Fetching times..."):
        response = cli_auth.api_request("GET", path)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    times = response.json()

    if not times:
        console.print("[yellow]No swim times found[/yellow]")
        return

    table = Table(title=f"Swim Times ({len(times)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Time", style="green", no_wrap=True)
    table.add_column("Date", no_wrap=True)
    table.add_column("Round", no_wrap=True)

    for time in times:
        table.add_row(
            time["id"][:8],
            time.get("time_formatted", "-"),
            time.get("swim_date", "-"),
            time.get("round") or "-",
        )

    console.print(table)


@times_app.command("record")
def times_record(
    swimmer: str = typer.Option(..., "--swimmer", "-s", help="Swimmer ID or name"),
    meet: str = typer.Option(..., "--meet", "-m", help="Meet ID or name"),
    event: str = typer.Option(..., "--event", "-e", help="Event (e.g., '100 free scy')"),
    time: str = typer.Option(..., "--time", "-t", help="Time (e.g., '1:05.23' or '32.45')"),
    team: str = typer.Option(..., "--team", help="Team ID or name"),
    date: str = typer.Option(..., "--date", "-d", help="Swim date (YYYY-MM-DD)"),
    round_name: str = typer.Option(None, "--round", "-r", help="Round (prelims/finals/consolation/time_trial)"),
    lane: int = typer.Option(None, "--lane", help="Lane number (1-10)"),
    place: int = typer.Option(None, "--place", help="Finish place"),
):
    """Record a swim time (admin or coach only)."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Parse event
    try:
        distance, stroke, course = _parse_event(event)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve swimmer, meet, team
    with console.status("Resolving references..."):
        swimmer_data = _resolve_swimmer(swimmer)
        meet_data = _resolve_meet(meet)
        team_data = _resolve_team(team)

    swimmer_id = swimmer_data["id"]
    meet_id = meet_data["id"]
    team_id = team_data["id"]
    swimmer_name = f"{swimmer_data['first_name']} {swimmer_data['last_name']}"

    # Find or create event - for now we'll need to look up or create the event
    # The API needs the event_id, so we need to find it first
    # For simplicity, we'll use a simple approach: query events to find match
    event_response = cli_auth.api_request(
        "GET",
        f"/api/v1/time-standards?stroke={stroke}&distance={distance}&course={course}&limit=1"
    )
    event_id = None

    # If we can't find the event via time standards, we need another approach
    # For now, let's assume the event exists and use a placeholder
    # In a real implementation, we'd have an events API
    console.print("[yellow]Note: Event lookup is simplified - event must already exist[/yellow]")

    payload = {
        "swimmer_id": swimmer_id,
        "meet_id": meet_id,
        "team_id": team_id,
        "time_formatted": time,
        "swim_date": date,
    }

    # We need event_id - for now, let's report this limitation
    console.print("[red]Error: Recording times requires event_id. Event API not yet implemented.[/red]")
    console.print("[dim]This feature will work once the events API is complete.[/dim]")
    raise typer.Exit(1)


@times_app.command("pbs")
def times_pbs(
    swimmer: str = typer.Argument(..., help="Swimmer ID or name"),
):
    """Show personal bests for a swimmer."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Resolve swimmer
    with console.status("Finding swimmer..."):
        swimmer_data = _resolve_swimmer(swimmer)

    swimmer_id = swimmer_data["id"]
    swimmer_name = f"{swimmer_data['first_name']} {swimmer_data['last_name']}"

    with console.status("Fetching personal bests..."):
        response = cli_auth.api_request("GET", f"/api/v1/swimmers/{swimmer_id}/personal-bests")

    if response.status_code == 404:
        console.print("[red]Swimmer not found[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    times = response.json()

    if not times:
        console.print(f"[yellow]No times recorded for {swimmer_name}[/yellow]")
        return

    table = Table(title=f"Personal Bests for {swimmer_name}")
    table.add_column("Time", style="green", no_wrap=True)
    table.add_column("Date", no_wrap=True)

    for time in times:
        table.add_row(
            time.get("time_formatted", "-"),
            time.get("swim_date", "-"),
        )

    console.print(table)


@times_app.command("compare")
def times_compare(
    time_id: str = typer.Argument(..., help="Swim time ID"),
):
    """Compare a swim time to personal best."""
    try:
        cli_auth.require_auth()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    with console.status("Analyzing time..."):
        response = cli_auth.api_request("GET", f"/api/v1/swim-times/analysis/{time_id}")

    if response.status_code == 404:
        console.print("[red]Swim time not found[/red]")
        raise typer.Exit(1)

    if response.status_code != 200:
        console.print(f"[red]Error: {response.text}[/red]")
        raise typer.Exit(1)

    data = response.json()

    table = Table(title="Time Analysis")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Time", data.get("time_formatted", "-"))
    table.add_row("Date", data.get("swim_date", "-"))
    table.add_row("Round", data.get("round") or "-")

    if data.get("is_personal_best"):
        table.add_row("Status", "[green bold]PERSONAL BEST![/green bold]")
    else:
        pb = data.get("personal_best")
        if pb:
            table.add_row("Personal Best", pb.get("time_formatted", "-"))
            time_off = data.get("time_off_pb")
            if time_off is not None:
                if time_off > 0:
                    table.add_row("Off PB", f"[red]+{time_off:.2f}s[/red]")
                else:
                    table.add_row("Off PB", f"[green]{time_off:.2f}s[/green]")

            improvement = data.get("improvement_percentage")
            if improvement is not None:
                if improvement > 0:
                    table.add_row("Improvement", f"[green]{improvement:.2f}%[/green]")
                else:
                    table.add_row("Improvement", f"[red]{improvement:.2f}%[/red]")
        else:
            table.add_row("Status", "[yellow]First time in this event[/yellow]")

    console.print(table)


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
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Display Name", style="cyan", no_wrap=True)
    table.add_column("Role", no_wrap=True)

    for user in users:
        role_color = {
            "admin": "red",
            "coach": "blue",
            "swimmer": "green",
            "fan": "yellow",
        }.get(user["role"], "white")

        table.add_row(
            user["id"][:8],
            user.get("display_name", "-"),
            f"[{role_color}]{user['role']}[/{role_color}]",
        )

    console.print(table)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
