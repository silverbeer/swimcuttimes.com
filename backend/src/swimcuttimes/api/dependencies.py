"""FastAPI dependencies for dependency injection.

Usage in routes:
    from swimcuttimes.api.dependencies import get_supabase, get_time_standard_dao

    @router.get("/time-standards")
    def list_time_standards(dao: TimeStandardDAO = Depends(get_time_standard_dao)):
        return dao.search()
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from supabase import Client, create_client

from swimcuttimes.config import Settings, get_settings
from swimcuttimes.dao.event_dao import EventDAO
from swimcuttimes.dao.meet_dao import MeetDAO
from swimcuttimes.dao.suit_dao import SuitModelDAO, SwimmerSuitDAO
from swimcuttimes.dao.swim_time_dao import SwimTimeDAO
from swimcuttimes.dao.swimmer_dao import SwimmerDAO
from swimcuttimes.dao.team_dao import SwimmerTeamDAO, TeamDAO
from swimcuttimes.dao.time_standard_dao import TimeStandardDAO
from swimcuttimes.dao.time_standard_definition_dao import TimeStandardDefinitionDAO


def get_settings_dep() -> Settings:
    """Get application settings (dependency wrapper)."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


@lru_cache
def get_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    """Create cached Supabase client."""
    return create_client(supabase_url, supabase_key)


def get_supabase(settings: SettingsDep) -> Client:
    """Get Supabase client for database operations."""
    return get_supabase_client(
        settings.supabase_url,
        settings.supabase_key.get_secret_value(),
    )


SupabaseDep = Annotated[Client, Depends(get_supabase)]


def get_event_dao(client: SupabaseDep) -> EventDAO:
    """Get EventDAO instance."""
    return EventDAO(client)


def get_team_dao(client: SupabaseDep) -> TeamDAO:
    """Get TeamDAO instance."""
    return TeamDAO(client)


def get_time_standard_dao(client: SupabaseDep) -> TimeStandardDAO:
    """Get TimeStandardDAO instance."""
    return TimeStandardDAO(client)


def get_time_standard_definition_dao(client: SupabaseDep) -> TimeStandardDefinitionDAO:
    """Get TimeStandardDefinitionDAO instance."""
    return TimeStandardDefinitionDAO(client)


def get_swimmer_dao(client: SupabaseDep) -> SwimmerDAO:
    """Get SwimmerDAO instance."""
    return SwimmerDAO(client)


def get_swimmer_team_dao(client: SupabaseDep) -> SwimmerTeamDAO:
    """Get SwimmerTeamDAO instance."""
    return SwimmerTeamDAO(client)


def get_meet_dao(client: SupabaseDep) -> MeetDAO:
    """Get MeetDAO instance."""
    return MeetDAO(client)


def get_swim_time_dao(client: SupabaseDep) -> SwimTimeDAO:
    """Get SwimTimeDAO instance."""
    return SwimTimeDAO(client)


def get_suit_model_dao(client: SupabaseDep) -> SuitModelDAO:
    """Get SuitModelDAO instance."""
    return SuitModelDAO(client)


def get_swimmer_suit_dao(client: SupabaseDep) -> SwimmerSuitDAO:
    """Get SwimmerSuitDAO instance."""
    return SwimmerSuitDAO(client)


EventDAODep = Annotated[EventDAO, Depends(get_event_dao)]
TeamDAODep = Annotated[TeamDAO, Depends(get_team_dao)]
TimeStandardDAODep = Annotated[TimeStandardDAO, Depends(get_time_standard_dao)]
TimeStandardDefinitionDAODep = Annotated[TimeStandardDefinitionDAO, Depends(get_time_standard_definition_dao)]
SwimmerDAODep = Annotated[SwimmerDAO, Depends(get_swimmer_dao)]
SwimmerTeamDAODep = Annotated[SwimmerTeamDAO, Depends(get_swimmer_team_dao)]
MeetDAODep = Annotated[MeetDAO, Depends(get_meet_dao)]
SwimTimeDAODep = Annotated[SwimTimeDAO, Depends(get_swim_time_dao)]
SuitModelDAODep = Annotated[SuitModelDAO, Depends(get_suit_model_dao)]
SwimmerSuitDAODep = Annotated[SwimmerSuitDAO, Depends(get_swimmer_suit_dao)]
