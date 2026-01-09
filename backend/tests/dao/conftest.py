"""Fixtures for DAO tests."""

import pytest
from dotenv import load_dotenv

# Load environment variables before importing DAOs
load_dotenv()


@pytest.fixture
def time_standard_dao():
    """Provide a TimeStandardDAO instance."""
    from swimcuttimes.dao import TimeStandardDAO

    return TimeStandardDAO()


@pytest.fixture
def event_dao():
    """Provide an EventDAO instance."""
    from swimcuttimes.dao import EventDAO

    return EventDAO()
