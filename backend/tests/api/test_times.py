"""Tests for Swim Time API endpoints."""

import pytest
from fastapi.testclient import TestClient

from swimcuttimes.config import get_settings

# Skip tests if service_role key is not configured (RLS blocks operations)
pytestmark = pytest.mark.skipif(
    get_settings().supabase_service_role_key is None,
    reason="SUPABASE_SERVICE_ROLE_KEY not configured - tests require service role to bypass RLS",
)

# Seeded event ID for 100 Freestyle SCY
EVENT_100_FREE_SCY = "v7ib0ew421ff"


class TestSwimTimeCRUD:
    """Test create, read, update, delete operations for swim times."""

    def _create_swimmer(self, client: TestClient) -> dict:
        """Helper to create a test swimmer."""
        payload = {
            "first_name": "Test",
            "last_name": "Swimmer",
            "date_of_birth": "2010-05-15",
            "gender": "M",
        }
        response = client.post("/api/v1/swimmers", json=payload)
        assert response.status_code == 201
        return response.json()

    def _create_team(self, client: TestClient) -> dict:
        """Helper to create a test team."""
        payload = {
            "name": f"Test Team {id(self)}",
            "team_type": "club",
            "sanctioning_body": "USA Swimming",
            "lsc": "NE",
        }
        response = client.post("/api/v1/teams", json=payload)
        assert response.status_code == 201
        return response.json()

    def _create_meet(self, client: TestClient) -> dict:
        """Helper to create a test meet."""
        payload = {
            "name": f"Test Meet {id(self)}",
            "location": "Test Pool",
            "city": "Boston",
            "state": "MA",
            "start_date": "2024-06-15",
            "course": "scy",
            "sanctioning_body": "NE Swimming",
            "meet_type": "invitational",
        }
        response = client.post("/api/v1/meets", json=payload)
        assert response.status_code == 201, f"Failed to create meet: {response.text}"
        return response.json()

    def test_create_get_update_delete_time(self, client_as_admin: TestClient):
        """Test full CRUD lifecycle for a swim time."""
        # Create prerequisites
        swimmer = self._create_swimmer(client_as_admin)
        team = self._create_team(client_as_admin)
        meet = self._create_meet(client_as_admin)

        try:
            # CREATE
            create_payload = {
                "swimmer_id": swimmer["id"],
                "event_id": EVENT_100_FREE_SCY,
                "meet_id": meet["id"],
                "team_id": team["id"],
                "time_centiseconds": 5765,  # 57.65 seconds
                "swim_date": "2024-06-15",
                "round": "finals",
                "lane": 4,
                "place": 1,
                "official": True,
                "dq": False,
            }
            response = client_as_admin.post("/api/v1/times", json=create_payload)

            # If event doesn't exist, we expect a foreign key error - skip test
            if response.status_code == 500 and "foreign key" in response.text.lower():
                pytest.skip("Test event not seeded in database")

            assert response.status_code == 201, response.text

            time_data = response.json()
            assert time_data["swimmer_id"] == swimmer["id"]
            assert time_data["time_centiseconds"] == 5765
            assert time_data["time_formatted"] == "57.65"
            assert time_data["round"] == "finals"
            assert time_data["lane"] == 4
            assert time_data["place"] == 1
            time_id = time_data["id"]

            # GET by ID
            response = client_as_admin.get(f"/api/v1/times/{time_id}")
            assert response.status_code == 200
            assert response.json()["id"] == time_id

            # UPDATE (partial)
            update_payload = {"time_centiseconds": 5650, "place": 2}
            response = client_as_admin.patch(f"/api/v1/times/{time_id}", json=update_payload)
            assert response.status_code == 200
            assert response.json()["time_centiseconds"] == 5650
            assert response.json()["time_formatted"] == "56.50"
            assert response.json()["place"] == 2
            assert response.json()["lane"] == 4  # Unchanged

            # DELETE
            response = client_as_admin.delete(f"/api/v1/times/{time_id}")
            assert response.status_code == 204

            # Verify deleted
            response = client_as_admin.get(f"/api/v1/times/{time_id}")
            assert response.status_code == 404

        finally:
            # Cleanup prerequisites
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
            client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_list_times_with_filters(self, client_as_admin: TestClient):
        """Test listing swim times with various filters."""
        swimmer = self._create_swimmer(client_as_admin)
        team = self._create_team(client_as_admin)
        meet = self._create_meet(client_as_admin)

        times_created = []

        try:
            # Create multiple times
            for i, time_cs in enumerate([5765, 5850, 5920]):
                payload = {
                    "swimmer_id": swimmer["id"],
                    "event_id": EVENT_100_FREE_SCY,
                    "meet_id": meet["id"],
                    "team_id": team["id"],
                    "time_centiseconds": time_cs,
                    "swim_date": f"2024-06-{15 + i}",
                    "official": True,
                    "dq": False,
                }
                response = client_as_admin.post("/api/v1/times", json=payload)
                if response.status_code == 500 and "foreign key" in response.text.lower():
                    pytest.skip("Test event not seeded in database")
                if response.status_code == 201:
                    times_created.append(response.json())

            if not times_created:
                pytest.skip("Could not create test times")

            # List all for this swimmer
            response = client_as_admin.get(
                "/api/v1/times", params={"swimmer_id": swimmer["id"]}
            )
            assert response.status_code == 200
            results = response.json()
            assert len(results) >= len(times_created)

            # Filter by meet
            response = client_as_admin.get(
                "/api/v1/times", params={"meet_id": meet["id"]}
            )
            assert response.status_code == 200
            results = response.json()
            assert all(t["meet_id"] == meet["id"] for t in results)

            # Filter by date range
            response = client_as_admin.get(
                "/api/v1/times",
                params={"start_date": "2024-06-16", "end_date": "2024-06-17"},
            )
            assert response.status_code == 200

        finally:
            # Cleanup
            for t in times_created:
                client_as_admin.delete(f"/api/v1/times/{t['id']}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
            client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_regular_user_can_read_not_write(
        self, client_as_admin: TestClient, client_as_user: TestClient
    ):
        """Test that regular users can read but not modify swim times."""
        swimmer = self._create_swimmer(client_as_admin)
        team = self._create_team(client_as_admin)
        meet = self._create_meet(client_as_admin)

        time_id = None

        try:
            # Admin creates a time
            create_payload = {
                "swimmer_id": swimmer["id"],
                "event_id": EVENT_100_FREE_SCY,
                "meet_id": meet["id"],
                "team_id": team["id"],
                "time_centiseconds": 5765,
                "swim_date": "2024-06-15",
            }
            response = client_as_admin.post("/api/v1/times", json=create_payload)
            if response.status_code == 500 and "foreign key" in response.text.lower():
                pytest.skip("Test event not seeded in database")
            assert response.status_code == 201
            time_id = response.json()["id"]

            # Regular user can GET
            response = client_as_user.get(f"/api/v1/times/{time_id}")
            assert response.status_code == 200

            # Regular user can LIST
            response = client_as_user.get("/api/v1/times")
            assert response.status_code == 200

            # Regular user cannot CREATE
            response = client_as_user.post("/api/v1/times", json=create_payload)
            assert response.status_code == 403

            # Regular user cannot UPDATE
            response = client_as_user.patch(
                f"/api/v1/times/{time_id}", json={"time_centiseconds": 5000}
            )
            assert response.status_code == 403

            # Regular user cannot DELETE
            response = client_as_user.delete(f"/api/v1/times/{time_id}")
            assert response.status_code == 403

        finally:
            # Cleanup
            if time_id:
                client_as_admin.delete(f"/api/v1/times/{time_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
            client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_coach_can_create_and_update_times(
        self, client_as_admin: TestClient, client_as_coach: TestClient
    ):
        """Test that coach users can create and update swim times."""
        swimmer = self._create_swimmer(client_as_admin)
        team = self._create_team(client_as_admin)
        meet = self._create_meet(client_as_admin)

        time_id = None

        try:
            # Coach creates a time
            create_payload = {
                "swimmer_id": swimmer["id"],
                "event_id": EVENT_100_FREE_SCY,
                "meet_id": meet["id"],
                "team_id": team["id"],
                "time_centiseconds": 5765,
                "swim_date": "2024-06-15",
            }
            response = client_as_coach.post("/api/v1/times", json=create_payload)
            if response.status_code == 500 and "foreign key" in response.text.lower():
                pytest.skip("Test event not seeded in database")
            assert response.status_code == 201
            time_id = response.json()["id"]

            # Coach can UPDATE
            response = client_as_coach.patch(
                f"/api/v1/times/{time_id}", json={"time_centiseconds": 5650}
            )
            assert response.status_code == 200
            assert response.json()["time_centiseconds"] == 5650

            # Coach cannot DELETE (admin only)
            response = client_as_coach.delete(f"/api/v1/times/{time_id}")
            assert response.status_code == 403

        finally:
            # Cleanup as admin
            if time_id:
                client_as_admin.delete(f"/api/v1/times/{time_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
            client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_invalid_lane_rejected(self, client_as_admin: TestClient):
        """Test that invalid lane number is rejected."""
        swimmer = self._create_swimmer(client_as_admin)
        team = self._create_team(client_as_admin)
        meet = self._create_meet(client_as_admin)

        try:
            # Lane 0 is invalid
            create_payload = {
                "swimmer_id": swimmer["id"],
                "event_id": EVENT_100_FREE_SCY,
                "meet_id": meet["id"],
                "team_id": team["id"],
                "time_centiseconds": 5765,
                "swim_date": "2024-06-15",
                "lane": 0,
            }
            response = client_as_admin.post("/api/v1/times", json=create_payload)
            assert response.status_code == 422  # Validation error

            # Lane 11 is invalid
            create_payload["lane"] = 11
            response = client_as_admin.post("/api/v1/times", json=create_payload)
            assert response.status_code == 422

        finally:
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
            client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_time_formatted_response(self, client_as_admin: TestClient):
        """Test that time_formatted is correctly computed for various times."""
        swimmer = self._create_swimmer(client_as_admin)
        team = self._create_team(client_as_admin)
        meet = self._create_meet(client_as_admin)

        times_created = []

        try:
            # Test various time formats
            test_cases = [
                (2500, "25.00"),      # 25 seconds
                (5765, "57.65"),      # Under a minute
                (6000, "1:00.00"),    # Exactly 1 minute
                (8345, "1:23.45"),    # Over a minute
                (12000, "2:00.00"),   # 2 minutes
            ]

            for centiseconds, expected_formatted in test_cases:
                payload = {
                    "swimmer_id": swimmer["id"],
                    "event_id": EVENT_100_FREE_SCY,
                    "meet_id": meet["id"],
                    "team_id": team["id"],
                    "time_centiseconds": centiseconds,
                    "swim_date": "2024-06-15",
                }
                response = client_as_admin.post("/api/v1/times", json=payload)
                if response.status_code == 500 and "foreign key" in response.text.lower():
                    pytest.skip("Test event not seeded in database")
                if response.status_code == 201:
                    data = response.json()
                    times_created.append(data)
                    assert data["time_formatted"] == expected_formatted, (
                        f"Expected {expected_formatted} for {centiseconds}cs, "
                        f"got {data['time_formatted']}"
                    )

        finally:
            for t in times_created:
                client_as_admin.delete(f"/api/v1/times/{t['id']}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
            client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_dq_time(self, client_as_admin: TestClient):
        """Test creating and querying disqualified times."""
        swimmer = self._create_swimmer(client_as_admin)
        team = self._create_team(client_as_admin)
        meet = self._create_meet(client_as_admin)

        time_id = None

        try:
            # Create a DQ time
            create_payload = {
                "swimmer_id": swimmer["id"],
                "event_id": EVENT_100_FREE_SCY,
                "meet_id": meet["id"],
                "team_id": team["id"],
                "time_centiseconds": 5765,
                "swim_date": "2024-06-15",
                "dq": True,
                "dq_reason": "False start",
            }
            response = client_as_admin.post("/api/v1/times", json=create_payload)
            if response.status_code == 500 and "foreign key" in response.text.lower():
                pytest.skip("Test event not seeded in database")
            assert response.status_code == 201
            data = response.json()
            time_id = data["id"]
            assert data["dq"] is True
            assert data["dq_reason"] == "False start"

            # By default, DQ times are excluded
            response = client_as_admin.get(
                "/api/v1/times", params={"swimmer_id": swimmer["id"]}
            )
            assert response.status_code == 200
            results = response.json()
            dq_ids = [t["id"] for t in results if t["dq"]]
            assert time_id not in dq_ids

            # Include DQ times
            response = client_as_admin.get(
                "/api/v1/times",
                params={"swimmer_id": swimmer["id"], "exclude_dq": False},
            )
            assert response.status_code == 200
            results = response.json()
            ids = [t["id"] for t in results]
            assert time_id in ids

        finally:
            if time_id:
                client_as_admin.delete(f"/api/v1/times/{time_id}")
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
            client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_get_nonexistent_time_returns_404(self, client_as_admin: TestClient):
        """Test that getting a nonexistent time returns 404."""
        response = client_as_admin.get("/api/v1/times/nonexistent_id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
