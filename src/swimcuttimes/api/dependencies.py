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
from swimcuttimes.dao.time_standard_dao import TimeStandardDAO


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


def get_time_standard_dao(client: SupabaseDep) -> TimeStandardDAO:
    """Get TimeStandardDAO instance."""
    return TimeStandardDAO(client)


EventDAODep = Annotated[EventDAO, Depends(get_event_dao)]
TimeStandardDAODep = Annotated[TimeStandardDAO, Depends(get_time_standard_dao)]
