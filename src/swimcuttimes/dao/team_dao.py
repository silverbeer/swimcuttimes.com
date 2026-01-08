"""Data Access Objects for Teams and Swimmer-Team associations."""

from datetime import date
from uuid import UUID

from supabase import Client
from swimcuttimes.dao.base import BaseDAO
from swimcuttimes.models.team import SwimmerTeam, Team, TeamType


class TeamDAO(BaseDAO[Team]):
    """DAO for Team entities."""

    table_name = "teams"
    model_class = Team

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_name(self, name: str) -> list[Team]:
        """Find teams by name (partial match).

        Args:
            name: Team name to search for

        Returns:
            List of matching Teams
        """
        result = self.table.select("*").ilike("name", f"%{name}%").execute()
        return [self._to_model(row) for row in result.data]

    def find_by_type(self, team_type: TeamType) -> list[Team]:
        """Find all teams of a specific type.

        Args:
            team_type: The type of team

        Returns:
            List of Teams of that type
        """
        result = self.table.select("*").eq("team_type", team_type.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_lsc(self, lsc: str) -> list[Team]:
        """Find club teams by LSC code.

        Args:
            lsc: LSC code (e.g., "NE", "PV")

        Returns:
            List of Teams in that LSC
        """
        result = self.table.select("*").eq("lsc", lsc).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_sanctioning_body(self, sanctioning_body: str) -> list[Team]:
        """Find teams by sanctioning body.

        Args:
            sanctioning_body: e.g., "USA Swimming", "NCAA D1"

        Returns:
            List of Teams under that sanctioning body
        """
        result = (
            self.table.select("*").eq("sanctioning_body", sanctioning_body).execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_division(self, division: str) -> list[Team]:
        """Find college teams by division.

        Args:
            division: e.g., "D1", "D2", "D3"

        Returns:
            List of college Teams in that division
        """
        result = self.table.select("*").eq("division", division).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_state(self, state: str) -> list[Team]:
        """Find teams by state.

        Args:
            state: State abbreviation

        Returns:
            List of Teams in that state
        """
        result = self.table.select("*").eq("state", state).execute()
        return [self._to_model(row) for row in result.data]

    def _to_model(self, row: dict) -> Team:
        """Convert database row to Team model."""
        return Team(
            id=UUID(row["id"]) if row.get("id") else None,
            name=row["name"],
            team_type=TeamType(row["team_type"]),
            sanctioning_body=row["sanctioning_body"],
            lsc=row.get("lsc"),
            division=row.get("division"),
            state=row.get("state"),
            country=row.get("country"),
        )

    def _to_db(self, model: Team) -> dict:
        """Convert Team model to database row."""
        data = {
            "name": model.name,
            "team_type": model.team_type.value,
            "sanctioning_body": model.sanctioning_body,
        }

        if model.id:
            data["id"] = str(model.id)
        if model.lsc:
            data["lsc"] = model.lsc
        if model.division:
            data["division"] = model.division
        if model.state:
            data["state"] = model.state
        if model.country:
            data["country"] = model.country

        return data


class SwimmerTeamDAO(BaseDAO[SwimmerTeam]):
    """DAO for SwimmerTeam associations (many-to-many with temporal data)."""

    table_name = "swimmer_teams"
    model_class = SwimmerTeam

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_swimmer(self, swimmer_id: UUID) -> list[SwimmerTeam]:
        """Find all team associations for a swimmer.

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of SwimmerTeam associations (all time)
        """
        result = (
            self.table.select("*").eq("swimmer_id", str(swimmer_id)).execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_current_by_swimmer(self, swimmer_id: UUID) -> list[SwimmerTeam]:
        """Find current team associations for a swimmer.

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of current SwimmerTeam associations (end_date is null)
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .is_("end_date", "null")
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_team(self, team_id: UUID) -> list[SwimmerTeam]:
        """Find all swimmer associations for a team.

        Args:
            team_id: The team's UUID

        Returns:
            List of SwimmerTeam associations (all time)
        """
        result = self.table.select("*").eq("team_id", str(team_id)).execute()
        return [self._to_model(row) for row in result.data]

    def find_current_by_team(self, team_id: UUID) -> list[SwimmerTeam]:
        """Find current swimmer associations for a team.

        Args:
            team_id: The team's UUID

        Returns:
            List of current SwimmerTeam associations
        """
        result = (
            self.table.select("*")
            .eq("team_id", str(team_id))
            .is_("end_date", "null")
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_swimmer_and_team(
        self, swimmer_id: UUID, team_id: UUID
    ) -> list[SwimmerTeam]:
        """Find all associations between a specific swimmer and team.

        Args:
            swimmer_id: The swimmer's UUID
            team_id: The team's UUID

        Returns:
            List of SwimmerTeam associations (may include historical)
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .eq("team_id", str(team_id))
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_active_on_date(
        self, swimmer_id: UUID, target_date: date
    ) -> list[SwimmerTeam]:
        """Find team associations active on a specific date.

        Args:
            swimmer_id: The swimmer's UUID
            target_date: The date to check

        Returns:
            List of SwimmerTeam associations active on that date
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .lte("start_date", target_date.isoformat())
            .or_(f"end_date.is.null,end_date.gte.{target_date.isoformat()}")
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def end_membership(self, id: UUID, end_date: date) -> SwimmerTeam | None:
        """End a team membership by setting the end date.

        Args:
            id: The SwimmerTeam association's UUID
            end_date: The date the membership ended

        Returns:
            The updated SwimmerTeam or None if not found
        """
        result = (
            self.table.update({"end_date": end_date.isoformat()})
            .eq("id", str(id))
            .execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def _to_model(self, row: dict) -> SwimmerTeam:
        """Convert database row to SwimmerTeam model."""
        return SwimmerTeam(
            id=UUID(row["id"]) if row.get("id") else None,
            swimmer_id=UUID(row["swimmer_id"]),
            team_id=UUID(row["team_id"]),
            start_date=date.fromisoformat(row["start_date"]),
            end_date=date.fromisoformat(row["end_date"]) if row.get("end_date") else None,
        )

    def _to_db(self, model: SwimmerTeam) -> dict:
        """Convert SwimmerTeam model to database row."""
        data = {
            "swimmer_id": str(model.swimmer_id),
            "team_id": str(model.team_id),
            "start_date": model.start_date.isoformat(),
        }

        if model.id:
            data["id"] = str(model.id)
        if model.end_date:
            data["end_date"] = model.end_date.isoformat()

        return data
