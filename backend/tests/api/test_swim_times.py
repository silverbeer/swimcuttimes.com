"""Tests for SwimTime API endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient

from swimcuttimes.config import get_settings

# Skip tests if service_role key is not configured (RLS blocks operations)
pytestmark = pytest.mark.skipif(
    get_settings().supabase_service_role_key is None,
    reason="SUPABASE_SERVICE_ROLE_KEY not configured - tests require service role to bypass RLS",
)


class TestSwimTimeHelpers:
    """Helper methods for swim time tests."""

    @staticmethod
    def create_swimmer(client: TestClient, first_name: str, last_name: str) -> str:
        """Create a test swimmer and return its ID."""
        response = client.post(
            "/api/v1/swimmers",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": "2008-05-15",
                "gender": "F",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    @staticmethod
    def create_team(client: TestClient, name: str) -> str:
        """Create a test team and return its ID."""
        # Add UUID suffix to ensure unique team names across test runs
        unique_name = f"{name} {uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/teams",
            json={
                "name": unique_name,
                "team_type": "high_school",
                "sanctioning_body": "MIAA",
                "state": "MA",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    @staticmethod
    def create_meet(client: TestClient, name: str) -> str:
        """Create a test meet and return its ID."""
        # Add UUID suffix to ensure unique meet names across test runs
        unique_name = f"{name} {uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/meets",
            json={
                "name": unique_name,
                "location": "Test Pool",
                "city": "Boston",
                "start_date": "2026-02-15",
                "course": "scy",
                "lanes": 6,
                "sanctioning_body": "MIAA",
                "meet_type": "dual",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    @staticmethod
    def get_or_create_event(client: TestClient, distance: int, stroke: str, course: str) -> str:
        """Get or create an event and return its ID.

        Note: This requires direct DB access since there's no events API yet.
        For now, we'll use the supabase client to create events directly.
        """
        # For tests, we need to create events directly in the database
        # This is a limitation until an events API is implemented
        from swimcuttimes.dao.event_dao import EventDAO
        from swimcuttimes.models import Course, Stroke

        settings = get_settings()
        from supabase import create_client

        key = settings.supabase_service_role_key or settings.supabase_key
        db_client = create_client(settings.supabase_url, key.get_secret_value())

        dao = EventDAO(db_client)
        event = dao.find_or_create(
            distance=distance,
            stroke=Stroke(stroke),
            course=Course(course),
        )
        return str(event.id)


class TestSwimTimeCRUD:
    """Test create, read, update, delete operations for swim times."""

    def test_record_and_retrieve_time(self, client_as_admin: TestClient):
        """Test recording a swim time and retrieving it."""
        helpers = TestSwimTimeHelpers()

        # Create required entities
        swimmer_id = helpers.create_swimmer(client_as_admin, "SwimTime", "TestSwimmer")
        team_id = helpers.create_team(client_as_admin, "SwimTime Test HS")
        meet_id = helpers.create_meet(client_as_admin, "SwimTime Test Meet")
        event_id = helpers.get_or_create_event(client_as_admin, 100, "freestyle", "scy")

        try:
            # Record a swim time
            create_payload = {
                "swimmer_id": swimmer_id,
                "event_id": event_id,
                "meet_id": meet_id,
                "team_id": team_id,
                "time_formatted": "58.45",
                "swim_date": "2026-02-15",
                "round": "finals",
                "lane": 4,
                "place": 1,
            }
            response = client_as_admin.post("/api/v1/swim-times", json=create_payload)
            assert response.status_code == 201, response.text

            time_data = response.json()
            assert time_data["time_formatted"] == "58.45"
            assert time_data["swimmer_id"] == swimmer_id
            assert time_data["event_id"] == event_id
            assert time_data["round"] == "finals"
            assert time_data["lane"] == 4
            assert time_data["place"] == 1
            time_id = time_data["id"]

            # Retrieve by ID
            response = client_as_admin.get(f"/api/v1/swim-times/{time_id}")
            assert response.status_code == 200
            assert response.json()["id"] == time_id

            # Update time
            response = client_as_admin.patch(
                f"/api/v1/swim-times/{time_id}",
                json={"time_formatted": "57.89", "place": 2},
            )
            assert response.status_code == 200
            assert response.json()["time_formatted"] == "57.89"
            assert response.json()["place"] == 2

            # Delete time
            response = client_as_admin.delete(f"/api/v1/swim-times/{time_id}")
            assert response.status_code == 204

            # Verify deleted
            response = client_as_admin.get(f"/api/v1/swim-times/{time_id}")
            assert response.status_code == 404

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")

    def test_time_in_centiseconds(self, client_as_admin: TestClient):
        """Test recording time using centiseconds directly."""
        helpers = TestSwimTimeHelpers()

        swimmer_id = helpers.create_swimmer(client_as_admin, "Centiseconds", "TestSwimmer")
        team_id = helpers.create_team(client_as_admin, "Centiseconds Test HS")
        meet_id = helpers.create_meet(client_as_admin, "Centiseconds Test Meet")
        event_id = helpers.get_or_create_event(client_as_admin, 50, "freestyle", "scy")

        try:
            # Record using centiseconds (25.43 seconds = 2543 centiseconds)
            create_payload = {
                "swimmer_id": swimmer_id,
                "event_id": event_id,
                "meet_id": meet_id,
                "team_id": team_id,
                "time_centiseconds": 2543,
                "swim_date": "2026-02-15",
            }
            response = client_as_admin.post("/api/v1/swim-times", json=create_payload)
            assert response.status_code == 201, response.text

            time_data = response.json()
            assert time_data["time_centiseconds"] == 2543
            assert time_data["time_formatted"] == "25.43"
            time_id = time_data["id"]

            # Cleanup
            client_as_admin.delete(f"/api/v1/swim-times/{time_id}")

        finally:
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")

    def test_list_times_with_filters(self, client_as_admin: TestClient):
        """Test listing swim times with various filters."""
        helpers = TestSwimTimeHelpers()

        swimmer_id = helpers.create_swimmer(client_as_admin, "Filter", "TestSwimmer")
        team_id = helpers.create_team(client_as_admin, "Filter Test HS")
        meet_id = helpers.create_meet(client_as_admin, "Filter Test Meet")
        event_id = helpers.get_or_create_event(client_as_admin, 100, "backstroke", "scy")

        time_ids = []
        try:
            # Create multiple times
            for i, time_str in enumerate(["1:05.23", "1:04.56", "1:06.12"]):
                response = client_as_admin.post(
                    "/api/v1/swim-times",
                    json={
                        "swimmer_id": swimmer_id,
                        "event_id": event_id,
                        "meet_id": meet_id,
                        "team_id": team_id,
                        "time_formatted": time_str,
                        "swim_date": f"2026-02-{15 + i}",
                    },
                )
                assert response.status_code == 201
                time_ids.append(response.json()["id"])

            # Filter by swimmer
            response = client_as_admin.get("/api/v1/swim-times", params={"swimmer_id": swimmer_id})
            assert response.status_code == 200
            times = response.json()
            assert len(times) == 3
            assert all(t["swimmer_id"] == swimmer_id for t in times)

            # Filter by meet
            response = client_as_admin.get("/api/v1/swim-times", params={"meet_id": meet_id})
            assert response.status_code == 200
            times = response.json()
            assert len(times) >= 3

            # Filter by team
            response = client_as_admin.get("/api/v1/swim-times", params={"team_id": team_id})
            assert response.status_code == 200
            times = response.json()
            assert len(times) >= 3

        finally:
            # Cleanup
            for time_id in time_ids:
                client_as_admin.delete(f"/api/v1/swim-times/{time_id}")
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")


class TestPersonalBests:
    """Test personal best tracking and analysis."""

    def test_personal_best_tracking(self, client_as_admin: TestClient):
        """Test that personal bests are correctly identified."""
        helpers = TestSwimTimeHelpers()

        swimmer_id = helpers.create_swimmer(client_as_admin, "PB", "TestSwimmer")
        team_id = helpers.create_team(client_as_admin, "PB Test HS")
        meet_id = helpers.create_meet(client_as_admin, "PB Test Meet")
        event_id = helpers.get_or_create_event(client_as_admin, 200, "freestyle", "scy")

        time_ids = []
        try:
            # Record multiple times - best is 1:58.00
            times = ["2:05.00", "1:58.00", "2:01.50"]
            for i, time_str in enumerate(times):
                response = client_as_admin.post(
                    "/api/v1/swim-times",
                    json={
                        "swimmer_id": swimmer_id,
                        "event_id": event_id,
                        "meet_id": meet_id,
                        "team_id": team_id,
                        "time_formatted": time_str,
                        "swim_date": f"2026-02-{15 + i}",
                    },
                )
                assert response.status_code == 201
                time_ids.append(response.json()["id"])

            # Get personal bests
            response = client_as_admin.get(f"/api/v1/swimmers/{swimmer_id}/personal-bests")
            assert response.status_code == 200
            pbs = response.json()

            # Should have one PB for the 200 free
            assert len(pbs) >= 1
            pb_for_event = [pb for pb in pbs if pb["event_id"] == event_id]
            assert len(pb_for_event) == 1
            assert pb_for_event[0]["time_formatted"] == "1:58.00"

        finally:
            # Cleanup
            for time_id in time_ids:
                client_as_admin.delete(f"/api/v1/swim-times/{time_id}")
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")

    def test_analysis_endpoint(self, client_as_admin: TestClient):
        """Test the time analysis endpoint."""
        helpers = TestSwimTimeHelpers()

        swimmer_id = helpers.create_swimmer(client_as_admin, "Analysis", "TestSwimmer")
        team_id = helpers.create_team(client_as_admin, "Analysis Test HS")
        meet_id = helpers.create_meet(client_as_admin, "Analysis Test Meet")
        event_id = helpers.get_or_create_event(client_as_admin, 100, "breaststroke", "scy")

        time_ids = []
        try:
            # Record a PB time first
            response = client_as_admin.post(
                "/api/v1/swim-times",
                json={
                    "swimmer_id": swimmer_id,
                    "event_id": event_id,
                    "meet_id": meet_id,
                    "team_id": team_id,
                    "time_formatted": "1:10.00",
                    "swim_date": "2026-02-15",
                },
            )
            assert response.status_code == 201
            pb_time_id = response.json()["id"]
            time_ids.append(pb_time_id)

            # Record a slower time
            response = client_as_admin.post(
                "/api/v1/swim-times",
                json={
                    "swimmer_id": swimmer_id,
                    "event_id": event_id,
                    "meet_id": meet_id,
                    "team_id": team_id,
                    "time_formatted": "1:12.50",
                    "swim_date": "2026-02-16",
                },
            )
            assert response.status_code == 201
            slower_time_id = response.json()["id"]
            time_ids.append(slower_time_id)

            # Analyze the PB time
            response = client_as_admin.get(f"/api/v1/swim-times/analysis/{pb_time_id}")
            assert response.status_code == 200
            analysis = response.json()
            assert analysis["is_personal_best"] is True

            # Analyze the slower time
            response = client_as_admin.get(f"/api/v1/swim-times/analysis/{slower_time_id}")
            assert response.status_code == 200
            analysis = response.json()
            assert analysis["is_personal_best"] is False
            assert analysis["personal_best"]["time_formatted"] == "1:10.00"
            # Time off PB: 1:12.50 - 1:10.00 = 2.50 seconds slower
            assert analysis["time_off_pb"] == 2.50

        finally:
            # Cleanup
            for time_id in time_ids:
                client_as_admin.delete(f"/api/v1/swim-times/{time_id}")
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")


class TestSwimTimePermissions:
    """Test permission checks for swim time operations."""

    def test_regular_user_can_read_times(
        self, client_as_admin: TestClient, client_as_user: TestClient
    ):
        """Test that regular users can read but not modify swim times."""
        helpers = TestSwimTimeHelpers()

        swimmer_id = helpers.create_swimmer(client_as_admin, "Permission", "TestSwimmer")
        team_id = helpers.create_team(client_as_admin, "Permission Test HS")
        meet_id = helpers.create_meet(client_as_admin, "Permission Test Meet")
        event_id = helpers.get_or_create_event(client_as_admin, 100, "butterfly", "scy")

        try:
            # Admin creates a time
            response = client_as_admin.post(
                "/api/v1/swim-times",
                json={
                    "swimmer_id": swimmer_id,
                    "event_id": event_id,
                    "meet_id": meet_id,
                    "team_id": team_id,
                    "time_formatted": "59.99",
                    "swim_date": "2026-02-15",
                },
            )
            assert response.status_code == 201
            time_id = response.json()["id"]

            # Regular user can GET
            response = client_as_user.get(f"/api/v1/swim-times/{time_id}")
            assert response.status_code == 200

            # Regular user can LIST
            response = client_as_user.get("/api/v1/swim-times")
            assert response.status_code == 200

            # Regular user cannot CREATE
            response = client_as_user.post(
                "/api/v1/swim-times",
                json={
                    "swimmer_id": swimmer_id,
                    "event_id": event_id,
                    "meet_id": meet_id,
                    "team_id": team_id,
                    "time_formatted": "1:00.00",
                    "swim_date": "2026-02-16",
                },
            )
            assert response.status_code == 403

            # Regular user cannot UPDATE
            response = client_as_user.patch(
                f"/api/v1/swim-times/{time_id}", json={"time_formatted": "0:01.00"}
            )
            assert response.status_code == 403

            # Regular user cannot DELETE
            response = client_as_user.delete(f"/api/v1/swim-times/{time_id}")
            assert response.status_code == 403

            # Cleanup as admin
            client_as_admin.delete(f"/api/v1/swim-times/{time_id}")

        finally:
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")

    def test_coach_can_manage_times(self, client_as_admin: TestClient, client_as_coach: TestClient):
        """Test that coaches can create, update, and delete swim times."""
        helpers = TestSwimTimeHelpers()

        swimmer_id = helpers.create_swimmer(client_as_admin, "CoachMgmt", "TestSwimmer")
        team_id = helpers.create_team(client_as_admin, "Coach Mgmt Test HS")
        meet_id = helpers.create_meet(client_as_admin, "Coach Mgmt Test Meet")
        event_id = helpers.get_or_create_event(client_as_admin, 50, "backstroke", "scy")

        try:
            # Coach can create
            response = client_as_coach.post(
                "/api/v1/swim-times",
                json={
                    "swimmer_id": swimmer_id,
                    "event_id": event_id,
                    "meet_id": meet_id,
                    "team_id": team_id,
                    "time_formatted": "28.50",
                    "swim_date": "2026-02-15",
                },
            )
            assert response.status_code == 201
            time_id = response.json()["id"]

            # Coach can update
            response = client_as_coach.patch(
                f"/api/v1/swim-times/{time_id}", json={"time_formatted": "27.99"}
            )
            assert response.status_code == 200
            assert response.json()["time_formatted"] == "27.99"

            # Coach can delete
            response = client_as_coach.delete(f"/api/v1/swim-times/{time_id}")
            assert response.status_code == 204

        finally:
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")
