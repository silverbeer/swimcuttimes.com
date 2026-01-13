"""Data Access Object for Swim Times."""

from datetime import date
from uuid import UUID

from supabase import Client
from swimcuttimes.dao.base import BaseDAO
from swimcuttimes.models.swim_time import Round, SwimTime


class SwimTimeDAO(BaseDAO[SwimTime]):
    """DAO for SwimTime entities."""

    table_name = "swim_times"
    model_class = SwimTime

    def __init__(self, client: Client | None = None):
        super().__init__(client)

    def find_by_swimmer(self, swimmer_id: UUID) -> list[SwimTime]:
        """Find all times for a swimmer.

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of SwimTimes for that swimmer
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .order("swim_date", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_swimmer_and_event(self, swimmer_id: UUID, event_id: UUID) -> list[SwimTime]:
        """Find all times for a swimmer in a specific event.

        Args:
            swimmer_id: The swimmer's UUID
            event_id: The event's UUID

        Returns:
            List of SwimTimes, ordered by date descending
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .eq("event_id", str(event_id))
            .order("swim_date", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_meet(self, meet_id: UUID) -> list[SwimTime]:
        """Find all times from a specific meet.

        Args:
            meet_id: The meet's UUID

        Returns:
            List of SwimTimes from that meet
        """
        result = self.table.select("*").eq("meet_id", str(meet_id)).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_team(self, team_id: UUID) -> list[SwimTime]:
        """Find all times swum for a specific team.

        Args:
            team_id: The team's UUID

        Returns:
            List of SwimTimes for that team
        """
        result = (
            self.table.select("*")
            .eq("team_id", str(team_id))
            .order("swim_date", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_by_round(self, round: Round) -> list[SwimTime]:
        """Find all times from a specific round.

        Args:
            round: The round type

        Returns:
            List of SwimTimes from that round
        """
        result = self.table.select("*").eq("round", round.value).execute()
        return [self._to_model(row) for row in result.data]

    def find_by_suit(self, suit_id: UUID) -> list[SwimTime]:
        """Find all times recorded with a specific suit.

        Args:
            suit_id: The swimmer suit's UUID

        Returns:
            List of SwimTimes using that suit
        """
        result = (
            self.table.select("*")
            .eq("suit_id", str(suit_id))
            .order("swim_date", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_times_with_suit(self, swimmer_id: UUID) -> list[SwimTime]:
        """Find all times for a swimmer that have a suit recorded.

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of SwimTimes with suit_id set
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .not_.is_("suit_id", "null")
            .order("swim_date", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_times_without_suit(self, swimmer_id: UUID) -> list[SwimTime]:
        """Find all times for a swimmer without a suit recorded.

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of SwimTimes without suit_id
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .is_("suit_id", "null")
            .order("swim_date", desc=True)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_personal_best(self, swimmer_id: UUID, event_id: UUID) -> SwimTime | None:
        """Find a swimmer's personal best (fastest time) for an event.

        Args:
            swimmer_id: The swimmer's UUID
            event_id: The event's UUID

        Returns:
            The fastest SwimTime or None if no times exist
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .eq("event_id", str(event_id))
            .eq("official", True)
            .eq("dq", False)
            .order("time_centiseconds")
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def find_all_personal_bests(self, swimmer_id: UUID) -> list[SwimTime]:
        """Find all personal bests for a swimmer (one per event).

        This uses a subquery approach to get the fastest time per event.

        Args:
            swimmer_id: The swimmer's UUID

        Returns:
            List of SwimTimes (one per event)
        """
        # Get all valid times grouped by event
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .eq("official", True)
            .eq("dq", False)
            .execute()
        )

        # Group by event and find fastest
        best_by_event: dict[str, SwimTime] = {}
        for row in result.data:
            st = self._to_model(row)
            event_id = str(row["event_id"])
            current_best = best_by_event.get(event_id)
            if current_best is None or st.time_centiseconds < current_best.time_centiseconds:
                best_by_event[event_id] = st

        return list(best_by_event.values())

    def find_by_date_range(self, swimmer_id: UUID, start: date, end: date) -> list[SwimTime]:
        """Find times for a swimmer within a date range.

        Args:
            swimmer_id: The swimmer's UUID
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of SwimTimes in that date range
        """
        result = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .gte("swim_date", start.isoformat())
            .lte("swim_date", end.isoformat())
            .order("swim_date")
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def find_faster_than(
        self, event_id: UUID, time_centiseconds: int, limit: int = 100
    ) -> list[SwimTime]:
        """Find all times faster than a given time for an event.

        Args:
            event_id: The event's UUID
            time_centiseconds: The time to compare against
            limit: Maximum results

        Returns:
            List of SwimTimes faster than the given time
        """
        result = (
            self.table.select("*")
            .eq("event_id", str(event_id))
            .eq("official", True)
            .eq("dq", False)
            .lt("time_centiseconds", time_centiseconds)
            .order("time_centiseconds")
            .limit(limit)
            .execute()
        )
        return [self._to_model(row) for row in result.data]

    def partial_update(self, id: str, updates: dict) -> SwimTime | None:
        """Update specific fields of a swim time.

        Args:
            id: Swim time ID (short ID string)
            updates: Dictionary of field names to new values

        Returns:
            Updated SwimTime or None if not found
        """
        # Filter out None values
        data = {k: v for k, v in updates.items() if v is not None}

        if not data:
            # No updates provided, return current swim time
            return self.get_by_id(id)

        result = self.table.update(data).eq("id", id).execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def find_existing(
        self,
        swimmer_id: str,
        event_id: str,
        meet_id: str,
        swim_date: date,
        round: Round | None = None,
    ) -> SwimTime | None:
        """Find an existing swim time by unique combination.

        Uniqueness key: swimmer + event + meet + date + round

        Args:
            swimmer_id: Swimmer's ID
            event_id: Event's ID
            meet_id: Meet's ID
            swim_date: Date of the swim
            round: Round of competition (optional)

        Returns:
            The SwimTime or None if not found
        """
        query = (
            self.table.select("*")
            .eq("swimmer_id", str(swimmer_id))
            .eq("event_id", str(event_id))
            .eq("meet_id", str(meet_id))
            .eq("swim_date", swim_date.isoformat())
        )

        if round:
            query = query.eq("round", round.value)
        else:
            query = query.is_("round", "null")

        result = query.execute()

        if not result.data:
            return None

        return self._to_model(result.data[0])

    def upsert(
        self,
        swimmer_id: str,
        event_id: str,
        meet_id: str,
        team_id: str,
        time_centiseconds: int,
        swim_date: date,
        round: Round | None = None,
        lane: int | None = None,
        place: int | None = None,
        official: bool = True,
        dq: bool = False,
        dq_reason: str | None = None,
        suit_id: str | None = None,
    ) -> tuple[SwimTime, str]:
        """Create or update a swim time.

        If a time exists for the same swimmer/event/meet/date/round,
        it will be updated. Otherwise, a new time is created.

        Args:
            swimmer_id: Swimmer's ID
            event_id: Event's ID
            meet_id: Meet's ID
            team_id: Team's ID
            time_centiseconds: Time in centiseconds
            swim_date: Date of the swim
            round: Round of competition
            lane: Lane number
            place: Finish place
            official: Whether official time
            dq: Whether disqualified
            dq_reason: DQ reason
            suit_id: Racing suit ID

        Returns:
            Tuple of (swim_time, action) where action is "created" or "updated"
        """
        # Check for existing time
        existing = self.find_existing(swimmer_id, event_id, meet_id, swim_date, round)

        if existing:
            # Update existing time
            updates = {
                "team_id": str(team_id),
                "time_centiseconds": time_centiseconds,
                "lane": lane,
                "place": place,
                "official": official,
                "dq": dq,
                "dq_reason": dq_reason,
            }
            if suit_id:
                updates["suit_id"] = str(suit_id)
            if round:
                updates["round"] = round.value

            result = self.table.update(updates).eq("id", existing.id).execute()
            return (self._to_model(result.data[0]), "updated")

        # Create new time
        new_time = SwimTime(
            swimmer_id=swimmer_id,
            event_id=event_id,
            meet_id=meet_id,
            team_id=team_id,
            time_centiseconds=time_centiseconds,
            swim_date=swim_date,
            round=round,
            lane=lane,
            place=place,
            official=official,
            dq=dq,
            dq_reason=dq_reason,
            suit_id=suit_id,
        )
        created = self.create(new_time)
        return (created, "created")

    def search(
        self,
        swimmer_id: str | None = None,
        event_id: str | None = None,
        meet_id: str | None = None,
        team_id: str | None = None,
        round: Round | None = None,
        official_only: bool = True,
        exclude_dq: bool = True,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[SwimTime]:
        """Search swim times with multiple filters.

        Args:
            swimmer_id: Filter by swimmer
            event_id: Filter by event
            meet_id: Filter by meet
            team_id: Filter by team
            round: Filter by round
            official_only: Only include official times
            exclude_dq: Exclude disqualified times
            start_date: Only times after this date
            end_date: Only times before this date
            limit: Maximum results

        Returns:
            List of matching SwimTimes
        """
        query = self.table.select("*")

        if swimmer_id:
            query = query.eq("swimmer_id", str(swimmer_id))
        if event_id:
            query = query.eq("event_id", str(event_id))
        if meet_id:
            query = query.eq("meet_id", str(meet_id))
        if team_id:
            query = query.eq("team_id", str(team_id))
        if round:
            query = query.eq("round", round.value)
        if official_only:
            query = query.eq("official", True)
        if exclude_dq:
            query = query.eq("dq", False)
        if start_date:
            query = query.gte("swim_date", start_date.isoformat())
        if end_date:
            query = query.lte("swim_date", end_date.isoformat())

        result = query.order("time_centiseconds").limit(limit).execute()
        return [self._to_model(row) for row in result.data]

    def _to_model(self, row: dict) -> SwimTime:
        """Convert database row to SwimTime model."""
        return SwimTime(
            id=row["id"] if row.get("id") else None,  # Short ID (TEXT), not UUID
            swimmer_id=row["swimmer_id"],  # Short ID (TEXT), not UUID
            event_id=row["event_id"],  # Short ID (TEXT), not UUID
            meet_id=row["meet_id"],  # Short ID (TEXT), not UUID
            time_centiseconds=row["time_centiseconds"],
            swim_date=date.fromisoformat(row["swim_date"]),
            team_id=row["team_id"],  # Short ID (TEXT), not UUID
            suit_id=row["suit_id"] if row.get("suit_id") else None,  # Short ID (TEXT), not UUID
            round=Round(row["round"]) if row.get("round") else None,
            lane=row.get("lane"),
            place=row.get("place"),
            official=row.get("official", True),
            dq=row.get("dq", False),
            dq_reason=row.get("dq_reason"),
        )

    def _to_db(self, model: SwimTime) -> dict:
        """Convert SwimTime model to database row."""
        data = {
            "swimmer_id": str(model.swimmer_id),
            "event_id": str(model.event_id),
            "meet_id": str(model.meet_id),
            "time_centiseconds": model.time_centiseconds,
            "swim_date": model.swim_date.isoformat(),
            "team_id": str(model.team_id),
            "official": model.official,
            "dq": model.dq,
        }

        if model.id:
            data["id"] = str(model.id)
        if model.suit_id:
            data["suit_id"] = str(model.suit_id)
        if model.round:
            data["round"] = model.round.value
        if model.lane is not None:
            data["lane"] = model.lane
        if model.place is not None:
            data["place"] = model.place
        if model.dq_reason:
            data["dq_reason"] = model.dq_reason

        return data
