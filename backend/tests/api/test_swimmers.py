"""Tests for Swimmer API endpoints."""

import pytest
from fastapi.testclient import TestClient

from swimcuttimes.config import get_settings

# Skip tests if service_role key is not configured (RLS blocks operations)
pytestmark = pytest.mark.skipif(
    get_settings().supabase_service_role_key is None,
    reason="SUPABASE_SERVICE_ROLE_KEY not configured - tests require service role to bypass RLS",
)


class TestSwimmerCRUD:
    """Test create, read, update, delete operations for swimmers."""

    def test_create_get_update_delete_swimmer(self, client_as_admin: TestClient):
        """Test full CRUD lifecycle for a swimmer."""
        # CREATE
        create_payload = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "2010-05-15",
            "gender": "M",
        }
        response = client_as_admin.post("/api/v1/swimmers", json=create_payload)
        assert response.status_code == 201, response.text

        swimmer = response.json()
        assert swimmer["first_name"] == "John"
        assert swimmer["last_name"] == "Doe"
        assert swimmer["date_of_birth"] == "2010-05-15"
        assert swimmer["gender"] == "M"
        assert swimmer["id"] is not None
        assert swimmer["age"] > 0  # Computed field
        assert swimmer["age_group"] is not None  # Computed field
        swimmer_id = swimmer["id"]

        # GET by ID
        response = client_as_admin.get(f"/api/v1/swimmers/{swimmer_id}")
        assert response.status_code == 200
        assert response.json()["id"] == swimmer_id
        assert response.json()["first_name"] == "John"

        # UPDATE (partial)
        update_payload = {"first_name": "Johnny", "usa_swimming_id": "12345678"}
        response = client_as_admin.patch(
            f"/api/v1/swimmers/{swimmer_id}", json=update_payload
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Johnny"
        assert response.json()["last_name"] == "Doe"  # Unchanged field preserved
        assert response.json()["usa_swimming_id"] == "12345678"

        # DELETE
        response = client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client_as_admin.get(f"/api/v1/swimmers/{swimmer_id}")
        assert response.status_code == 404

    def test_list_swimmers_with_filters(self, client_as_admin: TestClient):
        """Test listing swimmers with various filters."""
        # Create test swimmers
        swimmers = []
        test_data = [
            {
                "first_name": "Alice",
                "last_name": "TestFilter",
                "date_of_birth": "2012-01-01",
                "gender": "F",
            },
            {
                "first_name": "Bob",
                "last_name": "TestFilter",
                "date_of_birth": "2010-06-15",
                "gender": "M",
            },
            {
                "first_name": "Carol",
                "last_name": "Other",
                "date_of_birth": "2015-03-20",
                "gender": "F",
            },
        ]
        for data in test_data:
            response = client_as_admin.post("/api/v1/swimmers", json=data)
            assert response.status_code == 201
            swimmers.append(response.json())

        try:
            # List all
            response = client_as_admin.get("/api/v1/swimmers")
            assert response.status_code == 200
            assert isinstance(response.json(), list)

            # Filter by name (partial match)
            response = client_as_admin.get(
                "/api/v1/swimmers", params={"name": "TestFilter"}
            )
            assert response.status_code == 200
            results = response.json()
            assert len(results) >= 2
            assert all("TestFilter" in s["last_name"] for s in results)

            # Filter by gender
            response = client_as_admin.get("/api/v1/swimmers", params={"gender": "F"})
            assert response.status_code == 200
            results = response.json()
            assert all(s["gender"] == "F" for s in results)

            # Filter by age range
            response = client_as_admin.get(
                "/api/v1/swimmers", params={"min_age": 10, "max_age": 14}
            )
            assert response.status_code == 200
            results = response.json()
            assert all(10 <= s["age"] <= 14 for s in results)

        finally:
            # Cleanup
            for swimmer in swimmers:
                client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")

    def test_regular_user_can_read_not_write(
        self, client_as_admin: TestClient, client_as_user: TestClient
    ):
        """Test that regular users can read but not modify swimmers."""
        # Admin creates a swimmer
        create_payload = {
            "first_name": "ReadOnly",
            "last_name": "Swimmer",
            "date_of_birth": "2012-08-20",
            "gender": "M",
        }
        response = client_as_admin.post("/api/v1/swimmers", json=create_payload)
        assert response.status_code == 201
        swimmer_id = response.json()["id"]

        try:
            # Regular user can GET
            response = client_as_user.get(f"/api/v1/swimmers/{swimmer_id}")
            assert response.status_code == 200
            assert response.json()["first_name"] == "ReadOnly"

            # Regular user can LIST
            response = client_as_user.get("/api/v1/swimmers")
            assert response.status_code == 200

            # Regular user cannot CREATE
            response = client_as_user.post("/api/v1/swimmers", json=create_payload)
            assert response.status_code == 403

            # Regular user cannot UPDATE
            response = client_as_user.patch(
                f"/api/v1/swimmers/{swimmer_id}", json={"first_name": "Hacked"}
            )
            assert response.status_code == 403

            # Regular user cannot DELETE
            response = client_as_user.delete(f"/api/v1/swimmers/{swimmer_id}")
            assert response.status_code == 403

        finally:
            # Cleanup as admin
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")

    def test_coach_can_create_swimmers(
        self, client_as_admin: TestClient, client_as_coach: TestClient
    ):
        """Test that coach users can create and update swimmers."""
        # Coach creates a swimmer
        create_payload = {
            "first_name": "CoachCreated",
            "last_name": "Swimmer",
            "date_of_birth": "2011-04-10",
            "gender": "F",
        }
        response = client_as_coach.post("/api/v1/swimmers", json=create_payload)
        assert response.status_code == 201
        swimmer_id = response.json()["id"]

        try:
            # Coach can UPDATE
            response = client_as_coach.patch(
                f"/api/v1/swimmers/{swimmer_id}", json={"first_name": "Updated"}
            )
            assert response.status_code == 200
            assert response.json()["first_name"] == "Updated"

            # Coach cannot DELETE (admin only)
            response = client_as_coach.delete(f"/api/v1/swimmers/{swimmer_id}")
            assert response.status_code == 403

        finally:
            # Cleanup as admin
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")

    def test_duplicate_usa_swimming_id_rejected(self, client_as_admin: TestClient):
        """Test that creating a swimmer with duplicate USA Swimming ID returns 409."""
        create_payload = {
            "first_name": "First",
            "last_name": "Swimmer",
            "date_of_birth": "2010-01-01",
            "gender": "M",
            "usa_swimming_id": "UNIQUE123456",
        }

        # Create first swimmer
        response = client_as_admin.post("/api/v1/swimmers", json=create_payload)
        assert response.status_code == 201
        swimmer_id = response.json()["id"]

        try:
            # Try to create duplicate
            duplicate_payload = {
                "first_name": "Second",
                "last_name": "Swimmer",
                "date_of_birth": "2011-02-02",
                "gender": "F",
                "usa_swimming_id": "UNIQUE123456",  # Same ID
            }
            response = client_as_admin.post("/api/v1/swimmers", json=duplicate_payload)
            assert response.status_code == 409
            assert "exists" in response.json()["detail"]

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")


class TestSwimmerTeamAssignment:
    """Test swimmer-team assignment operations."""

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

    def _create_swimmer(self, client: TestClient, first_name: str = "Test") -> dict:
        """Helper to create a test swimmer."""
        payload = {
            "first_name": first_name,
            "last_name": "Swimmer",
            "date_of_birth": "2010-05-15",
            "gender": "M",
        }
        response = client.post("/api/v1/swimmers", json=payload)
        assert response.status_code == 201
        return response.json()

    def test_assign_swimmer_to_team(self, client_as_admin: TestClient):
        """Test basic swimmer-team assignment."""
        team = self._create_team(client_as_admin)
        swimmer = self._create_swimmer(client_as_admin)

        try:
            # Assign swimmer to team
            assign_payload = {"team_id": team["id"], "start_date": "2024-01-01"}
            response = client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams", json=assign_payload
            )
            assert response.status_code == 201

            assignment = response.json()
            assert assignment["swimmer_id"] == swimmer["id"]
            assert assignment["team_id"] == team["id"]
            assert assignment["team_name"] == team["name"]
            assert assignment["is_current"] is True

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")

    def test_swimmer_multiple_teams(self, client_as_admin: TestClient):
        """Test swimmer can be assigned to multiple teams concurrently."""
        team1 = self._create_team(client_as_admin)
        # Create second team with different name
        team2_payload = {
            "name": "Second Test Team",
            "team_type": "high_school",
            "sanctioning_body": "NFHS",
            "state": "MA",
        }
        response = client_as_admin.post("/api/v1/teams", json=team2_payload)
        assert response.status_code == 201
        team2 = response.json()

        swimmer = self._create_swimmer(client_as_admin)

        try:
            # Assign to first team
            response = client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                json={"team_id": team1["id"]},
            )
            assert response.status_code == 201

            # Assign to second team
            response = client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                json={"team_id": team2["id"]},
            )
            assert response.status_code == 201

            # List teams
            response = client_as_admin.get(f"/api/v1/swimmers/{swimmer['id']}/teams")
            assert response.status_code == 200
            teams = response.json()
            assert len(teams) == 2
            team_ids = {t["team_id"] for t in teams}
            assert team1["id"] in team_ids
            assert team2["id"] in team_ids

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team1['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team2['id']}")

    def test_end_team_membership(self, client_as_admin: TestClient):
        """Test ending a swimmer's team membership."""
        team = self._create_team(client_as_admin)
        swimmer = self._create_swimmer(client_as_admin)

        try:
            # Assign swimmer
            response = client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                json={"team_id": team["id"]},
            )
            assert response.status_code == 201
            assert response.json()["is_current"] is True

            # End membership
            response = client_as_admin.delete(
                f"/api/v1/swimmers/{swimmer['id']}/teams/{team['id']}",
                params={"end_date": "2024-12-31"},
            )
            assert response.status_code == 200
            assert response.json()["is_current"] is False
            assert response.json()["end_date"] == "2024-12-31"

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")

    def test_list_swimmer_teams_current_vs_history(self, client_as_admin: TestClient):
        """Test listing swimmer teams with current_only filter."""
        team1 = self._create_team(client_as_admin)
        team2_payload = {
            "name": "History Team",
            "team_type": "club",
            "sanctioning_body": "USA Swimming",
            "lsc": "CT",
        }
        response = client_as_admin.post("/api/v1/teams", json=team2_payload)
        assert response.status_code == 201
        team2 = response.json()

        swimmer = self._create_swimmer(client_as_admin)

        try:
            # Assign to both teams
            client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                json={"team_id": team1["id"]},
            )
            client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                json={"team_id": team2["id"]},
            )

            # End membership on team2
            client_as_admin.delete(
                f"/api/v1/swimmers/{swimmer['id']}/teams/{team2['id']}",
                params={"end_date": "2024-06-01"},
            )

            # List current only (default)
            response = client_as_admin.get(
                f"/api/v1/swimmers/{swimmer['id']}/teams", params={"current_only": True}
            )
            assert response.status_code == 200
            teams = response.json()
            assert len(teams) == 1
            assert teams[0]["team_id"] == team1["id"]

            # List all (including history)
            response = client_as_admin.get(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                params={"current_only": False},
            )
            assert response.status_code == 200
            teams = response.json()
            assert len(teams) == 2

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team1['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team2['id']}")

    def test_prevent_duplicate_active_membership(self, client_as_admin: TestClient):
        """Test that duplicate active membership to same team is prevented."""
        team = self._create_team(client_as_admin)
        swimmer = self._create_swimmer(client_as_admin)

        try:
            # First assignment
            response = client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                json={"team_id": team["id"]},
            )
            assert response.status_code == 201

            # Try duplicate assignment
            response = client_as_admin.post(
                f"/api/v1/swimmers/{swimmer['id']}/teams",
                json={"team_id": team["id"]},
            )
            assert response.status_code == 409
            assert "already a current member" in response.json()["detail"]

        finally:
            # Cleanup
            client_as_admin.delete(f"/api/v1/swimmers/{swimmer['id']}")
            client_as_admin.delete(f"/api/v1/teams/{team['id']}")
