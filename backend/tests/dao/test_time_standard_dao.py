"""Smoke tests for TimeStandardDAO."""

from swimcuttimes.models import Course, Gender, Stroke


class TestTimeStandardDAO:
    """Smoke tests for TimeStandardDAO."""

    def test_search_returns_results(self, time_standard_dao):
        """Verify search returns time standards from the database."""
        results = time_standard_dao.search(limit=10)

        assert len(results) > 0
        assert all(ts.id is not None for ts in results)

    def test_search_by_gender_filters_correctly(self, time_standard_dao):
        """Verify search filters by gender."""
        results = time_standard_dao.search(gender=Gender.FEMALE, limit=10)

        assert len(results) > 0
        assert all(ts.gender == Gender.FEMALE for ts in results)

    def test_search_by_event_filters_correctly(self, time_standard_dao):
        """Verify search filters by stroke, distance, and course."""
        results = time_standard_dao.search(
            stroke=Stroke.FREESTYLE,
            distance=100,
            course=Course.SCY,
        )

        assert len(results) > 0
        for ts in results:
            assert ts.event.stroke == Stroke.FREESTYLE
            assert ts.event.distance == 100
            assert ts.event.course == Course.SCY

    def test_find_by_sanctioning_body(self, time_standard_dao):
        """Verify find_by_sanctioning_body returns correct results."""
        results = time_standard_dao.find_by_sanctioning_body("New England Swimming")

        assert len(results) > 0
        assert all(ts.sanctioning_body == "New England Swimming" for ts in results)

    def test_time_standard_has_event_data(self, time_standard_dao):
        """Verify time standards include nested event data."""
        results = time_standard_dao.search(limit=1)

        assert len(results) == 1
        ts = results[0]

        # Verify event is populated
        assert ts.event is not None
        assert ts.event.id is not None
        assert ts.event.stroke is not None
        assert ts.event.distance > 0
        assert ts.event.course is not None

    def test_time_formatted_property(self, time_standard_dao):
        """Verify time_formatted returns properly formatted time string."""
        results = time_standard_dao.search(limit=1)

        assert len(results) == 1
        ts = results[0]

        # time_formatted should be a string like "54.49" or "1:05.79"
        assert isinstance(ts.time_formatted, str)
        assert "." in ts.time_formatted  # Should have decimal
