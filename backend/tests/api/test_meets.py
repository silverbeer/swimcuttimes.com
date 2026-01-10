"""Tests for Meet API endpoints."""

import pytest
from fastapi.testclient import TestClient

from swimcuttimes.config import get_settings

# Skip tests if service_role key is not configured (RLS blocks operations)
pytestmark = pytest.mark.skipif(
    get_settings().supabase_service_role_key is None,
    reason="SUPABASE_SERVICE_ROLE_KEY not configured - tests require service role to bypass RLS",
)


class TestMeetCRUD:
    """Test create, read, update, delete operations for meets."""

    def test_create_get_update_delete_meet(self, client_as_admin: TestClient):
        """Test full CRUD lifecycle for a meet."""
        # CREATE
        create_payload = {
            "name": "Test Championship Meet",
            "location": "Test Aquatic Center",
            "city": "Boston",
            "state": "MA",
            "start_date": "2026-03-15",
            "course": "scy",
            "lanes": 8,
            "indoor": True,
            "sanctioning_body": "USA Swimming",
            "meet_type": "championship",
        }
        response = client_as_admin.post("/api/v1/meets", json=create_payload)
        assert response.status_code == 201, response.text

        meet = response.json()
        assert meet["name"] == "Test Championship Meet"
        assert meet["location"] == "Test Aquatic Center"
        assert meet["city"] == "Boston"
        assert meet["state"] == "MA"
        assert meet["course"] == "scy"
        assert meet["lanes"] == 8
        assert meet["meet_type"] == "championship"
        assert meet["id"] is not None
        meet_id = meet["id"]

        # GET by ID
        response = client_as_admin.get(f"/api/v1/meets/{meet_id}")
        assert response.status_code == 200
        assert response.json()["id"] == meet_id
        assert response.json()["name"] == "Test Championship Meet"

        # UPDATE (partial)
        update_payload = {"name": "Updated Championship Meet", "lanes": 6}
        response = client_as_admin.patch(f"/api/v1/meets/{meet_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Championship Meet"
        assert response.json()["lanes"] == 6
        assert response.json()["city"] == "Boston"  # Unchanged field preserved

        # DELETE
        response = client_as_admin.delete(f"/api/v1/meets/{meet_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client_as_admin.get(f"/api/v1/meets/{meet_id}")
        assert response.status_code == 404

    def test_create_high_school_dual_meet(self, client_as_admin: TestClient):
        """Test creating a high school dual meet."""
        create_payload = {
            "name": "Lincoln vs. Washington Dual",
            "location": "Lincoln High Pool",
            "city": "Boston",
            "state": "MA",
            "start_date": "2026-01-20",
            "course": "scy",
            "lanes": 6,
            "indoor": True,
            "sanctioning_body": "MIAA",
            "meet_type": "dual",
        }
        response = client_as_admin.post("/api/v1/meets", json=create_payload)
        assert response.status_code == 201

        meet = response.json()
        assert meet["meet_type"] == "dual"
        assert meet["sanctioning_body"] == "MIAA"
        assert meet["state"] == "MA"

        # Cleanup
        client_as_admin.delete(f"/api/v1/meets/{meet['id']}")

    def test_list_meets_with_filters(self, client_as_admin: TestClient):
        """Test listing meets with various filters."""
        # Create test meets
        meet1_payload = {
            "name": "Filter Test Meet 1",
            "location": "Pool A",
            "city": "Cambridge",
            "start_date": "2026-02-01",
            "course": "scy",
            "lanes": 8,
            "sanctioning_body": "USA Swimming",
            "meet_type": "invitational",
        }
        response = client_as_admin.post("/api/v1/meets", json=meet1_payload)
        assert response.status_code == 201
        meet1_id = response.json()["id"]

        meet2_payload = {
            "name": "Filter Test Meet 2",
            "location": "Pool B",
            "city": "Worcester",
            "start_date": "2026-03-01",
            "course": "lcm",
            "lanes": 10,
            "sanctioning_body": "USA Swimming",
            "meet_type": "championship",
        }
        response = client_as_admin.post("/api/v1/meets", json=meet2_payload)
        assert response.status_code == 201
        meet2_id = response.json()["id"]

        try:
            # Filter by name
            response = client_as_admin.get("/api/v1/meets", params={"name": "Filter Test"})
            assert response.status_code == 200
            meets = response.json()
            assert len(meets) >= 2

            # Filter by course
            response = client_as_admin.get("/api/v1/meets", params={"course": "scy"})
            assert response.status_code == 200
            meets = response.json()
            assert all(m["course"] == "scy" for m in meets)

            # Filter by meet_type
            response = client_as_admin.get("/api/v1/meets", params={"meet_type": "championship"})
            assert response.status_code == 200
            meets = response.json()
            assert all(m["meet_type"] == "championship" for m in meets)

            # Filter by date range
            response = client_as_admin.get(
                "/api/v1/meets",
                params={"start_after": "2026-02-15", "start_before": "2026-03-15"},
            )
            assert response.status_code == 200
            meets = response.json()
            # Should include meet2 (March 1) but not meet1 (Feb 1)
            assert any(m["id"] == meet2_id for m in meets)
            assert not any(m["id"] == meet1_id for m in meets)

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/meets/{meet1_id}")
            client_as_admin.delete(f"/api/v1/meets/{meet2_id}")

    def test_invalid_lanes_rejected(self, client_as_admin: TestClient):
        """Test that invalid lane numbers are rejected."""
        create_payload = {
            "name": "Invalid Lanes Meet",
            "location": "Pool",
            "city": "Boston",
            "start_date": "2026-04-01",
            "course": "scy",
            "lanes": 7,  # Invalid - must be 6, 8, or 10
            "sanctioning_body": "USA Swimming",
            "meet_type": "invitational",
        }
        response = client_as_admin.post("/api/v1/meets", json=create_payload)
        assert response.status_code == 400
        assert "Lanes must be 6, 8, or 10" in response.json()["detail"]


class TestMeetTeams:
    """Test meet-team association operations."""

    def _create_team(self, client: TestClient, name: str) -> str:
        """Helper to create a test team and return its ID."""
        response = client.post(
            "/api/v1/teams",
            json={
                "name": name,
                "team_type": "high_school",
                "sanctioning_body": "MIAA",
                "state": "MA",
            },
        )
        assert response.status_code == 201
        return response.json()["id"]

    def _create_meet(self, client: TestClient, name: str) -> str:
        """Helper to create a test meet and return its ID."""
        response = client.post(
            "/api/v1/meets",
            json={
                "name": name,
                "location": "Test Pool",
                "city": "Boston",
                "start_date": "2026-02-15",
                "course": "scy",
                "lanes": 6,
                "sanctioning_body": "MIAA",
                "meet_type": "dual",
            },
        )
        assert response.status_code == 201
        return response.json()["id"]

    def test_add_team_to_meet(self, client_as_admin: TestClient):
        """Test adding a team to a meet."""
        # Create a meet and team
        meet_id = self._create_meet(client_as_admin, "Team Association Meet")
        team_id = self._create_team(client_as_admin, "Team Association Test HS")

        try:
            # Add team to meet
            response = client_as_admin.post(
                f"/api/v1/meets/{meet_id}/teams",
                json={"team_id": team_id, "is_host": True},
            )
            assert response.status_code == 201

            result = response.json()
            assert result["meet_id"] == meet_id
            assert result["team_id"] == team_id
            assert result["is_host"] is True
            assert result["team_name"] == "Team Association Test HS"

            # List teams in meet
            response = client_as_admin.get(f"/api/v1/meets/{meet_id}/teams")
            assert response.status_code == 200
            teams = response.json()
            assert len(teams) == 1
            assert teams[0]["team_id"] == team_id
            assert teams[0]["is_host"] is True

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")

    def test_add_multiple_teams_to_meet(self, client_as_admin: TestClient):
        """Test adding multiple teams to a dual/tri meet."""
        meet_id = self._create_meet(client_as_admin, "Multi-Team Meet")
        team1_id = self._create_team(client_as_admin, "Multi Team HS 1")
        team2_id = self._create_team(client_as_admin, "Multi Team HS 2")

        try:
            # Add host team
            response = client_as_admin.post(
                f"/api/v1/meets/{meet_id}/teams",
                json={"team_id": team1_id, "is_host": True},
            )
            assert response.status_code == 201

            # Add visiting team
            response = client_as_admin.post(
                f"/api/v1/meets/{meet_id}/teams",
                json={"team_id": team2_id, "is_host": False},
            )
            assert response.status_code == 201

            # List all teams
            response = client_as_admin.get(f"/api/v1/meets/{meet_id}/teams")
            assert response.status_code == 200
            teams = response.json()
            assert len(teams) == 2

            host_teams = [t for t in teams if t["is_host"]]
            assert len(host_teams) == 1
            assert host_teams[0]["team_id"] == team1_id

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team1_id}")
            client_as_admin.delete(f"/api/v1/teams/{team2_id}")

    def test_duplicate_team_in_meet_rejected(self, client_as_admin: TestClient):
        """Test that adding the same team twice returns 409."""
        meet_id = self._create_meet(client_as_admin, "Duplicate Team Meet")
        team_id = self._create_team(client_as_admin, "Duplicate Team Test HS")

        try:
            # Add team first time
            response = client_as_admin.post(
                f"/api/v1/meets/{meet_id}/teams",
                json={"team_id": team_id, "is_host": True},
            )
            assert response.status_code == 201

            # Try to add same team again
            response = client_as_admin.post(
                f"/api/v1/meets/{meet_id}/teams",
                json={"team_id": team_id, "is_host": False},
            )
            assert response.status_code == 409
            assert "already in this meet" in response.json()["detail"]

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")

    def test_remove_team_from_meet(self, client_as_admin: TestClient):
        """Test removing a team from a meet."""
        meet_id = self._create_meet(client_as_admin, "Remove Team Meet")
        team_id = self._create_team(client_as_admin, "Remove Team Test HS")

        try:
            # Add team
            response = client_as_admin.post(
                f"/api/v1/meets/{meet_id}/teams",
                json={"team_id": team_id, "is_host": False},
            )
            assert response.status_code == 201

            # Remove team
            response = client_as_admin.delete(f"/api/v1/meets/{meet_id}/teams/{team_id}")
            assert response.status_code == 204

            # Verify removed
            response = client_as_admin.get(f"/api/v1/meets/{meet_id}/teams")
            assert response.status_code == 200
            teams = response.json()
            assert len(teams) == 0

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
            client_as_admin.delete(f"/api/v1/teams/{team_id}")


class TestMeetPermissions:
    """Test permission checks for meet operations."""

    def test_regular_user_can_read_meets(
        self, client_as_admin: TestClient, client_as_user: TestClient
    ):
        """Test that regular users can read but not modify meets."""
        # Admin creates a meet
        create_payload = {
            "name": "Read Only Meet",
            "location": "Pool",
            "city": "Boston",
            "start_date": "2026-05-01",
            "course": "scy",
            "lanes": 8,
            "sanctioning_body": "USA Swimming",
            "meet_type": "invitational",
        }
        response = client_as_admin.post("/api/v1/meets", json=create_payload)
        assert response.status_code == 201
        meet_id = response.json()["id"]

        try:
            # Regular user can GET
            response = client_as_user.get(f"/api/v1/meets/{meet_id}")
            assert response.status_code == 200
            assert response.json()["name"] == "Read Only Meet"

            # Regular user can LIST
            response = client_as_user.get("/api/v1/meets")
            assert response.status_code == 200

            # Regular user cannot CREATE
            response = client_as_user.post("/api/v1/meets", json=create_payload)
            assert response.status_code == 403

            # Regular user cannot UPDATE
            response = client_as_user.patch(f"/api/v1/meets/{meet_id}", json={"name": "Hacked"})
            assert response.status_code == 403

            # Regular user cannot DELETE
            response = client_as_user.delete(f"/api/v1/meets/{meet_id}")
            assert response.status_code == 403

        finally:
            # Cleanup as admin
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")

    def test_coach_can_create_meets(self, client_as_admin: TestClient, client_as_coach: TestClient):
        """Test that coaches can create and update meets."""
        create_payload = {
            "name": "Coach Created Meet",
            "location": "Pool",
            "city": "Boston",
            "start_date": "2026-06-01",
            "course": "scy",
            "lanes": 6,
            "sanctioning_body": "MIAA",
            "meet_type": "dual",
        }
        response = client_as_coach.post("/api/v1/meets", json=create_payload)
        assert response.status_code == 201
        meet_id = response.json()["id"]

        try:
            # Coach can update
            response = client_as_coach.patch(
                f"/api/v1/meets/{meet_id}", json={"name": "Coach Updated Meet"}
            )
            assert response.status_code == 200

            # Coach cannot delete (admin only)
            response = client_as_coach.delete(f"/api/v1/meets/{meet_id}")
            assert response.status_code == 403

        finally:
            # Cleanup as admin
            client_as_admin.delete(f"/api/v1/meets/{meet_id}")
