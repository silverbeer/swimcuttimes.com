"""Tests for Team API endpoints."""

from fastapi.testclient import TestClient


class TestTeamCRUD:
    """Test create, read, update, delete operations for teams."""

    def test_create_get_update_delete_team(self, client_as_admin: TestClient):
        """Test full CRUD lifecycle for a club team."""
        # CREATE
        create_payload = {
            "name": "Test Swim Club",
            "team_type": "club",
            "sanctioning_body": "USA Swimming",
            "lsc": "NE",
        }
        response = client_as_admin.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 201, response.text

        team = response.json()
        assert team["name"] == "Test Swim Club"
        assert team["team_type"] == "club"
        assert team["sanctioning_body"] == "USA Swimming"
        assert team["lsc"] == "NE"
        assert team["id"] is not None
        team_id = team["id"]

        # GET by ID
        response = client_as_admin.get(f"/api/v1/teams/{team_id}")
        assert response.status_code == 200
        assert response.json()["id"] == team_id
        assert response.json()["name"] == "Test Swim Club"

        # UPDATE (partial)
        update_payload = {"name": "Updated Swim Club"}
        response = client_as_admin.patch(f"/api/v1/teams/{team_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Swim Club"
        assert response.json()["lsc"] == "NE"  # Unchanged field preserved

        # DELETE
        response = client_as_admin.delete(f"/api/v1/teams/{team_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client_as_admin.get(f"/api/v1/teams/{team_id}")
        assert response.status_code == 404

    def test_create_college_team(self, client_as_admin: TestClient):
        """Test creating a college team with required division."""
        create_payload = {
            "name": "State University Swimming",
            "team_type": "college",
            "sanctioning_body": "NCAA",
            "division": "D1",
        }
        response = client_as_admin.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 201

        team = response.json()
        assert team["team_type"] == "college"
        assert team["division"] == "D1"

        # Cleanup
        client_as_admin.delete(f"/api/v1/teams/{team['id']}")

    def test_create_high_school_team(self, client_as_admin: TestClient):
        """Test creating a high school team with required state."""
        create_payload = {
            "name": "Lincoln High School",
            "team_type": "high_school",
            "sanctioning_body": "NFHS",
            "state": "MA",
        }
        response = client_as_admin.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 201

        team = response.json()
        assert team["team_type"] == "high_school"
        assert team["state"] == "MA"

        # Cleanup
        client_as_admin.delete(f"/api/v1/teams/{team['id']}")

    def test_list_teams(self, client_as_admin: TestClient):
        """Test listing teams with filters."""
        # Create a test team
        create_payload = {
            "name": "Searchable Club",
            "team_type": "club",
            "sanctioning_body": "USA Swimming",
            "lsc": "CT",
        }
        response = client_as_admin.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 201
        team_id = response.json()["id"]

        # List all teams
        response = client_as_admin.get("/api/v1/teams")
        assert response.status_code == 200
        teams = response.json()
        assert isinstance(teams, list)
        assert len(teams) > 0

        # Filter by name
        response = client_as_admin.get("/api/v1/teams", params={"name": "Searchable"})
        assert response.status_code == 200
        teams = response.json()
        assert any(t["name"] == "Searchable Club" for t in teams)

        # Filter by team_type
        response = client_as_admin.get("/api/v1/teams", params={"team_type": "club"})
        assert response.status_code == 200
        teams = response.json()
        assert all(t["team_type"] == "club" for t in teams)

        # Cleanup
        client_as_admin.delete(f"/api/v1/teams/{team_id}")

    def test_duplicate_team_name_rejected(self, client_as_admin: TestClient):
        """Test that creating a team with a duplicate name returns 409."""
        create_payload = {
            "name": "Unique Test Club",
            "team_type": "club",
            "sanctioning_body": "USA Swimming",
            "lsc": "NE",
        }

        # Create first team
        response = client_as_admin.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 201
        team_id = response.json()["id"]

        # Try to create duplicate
        response = client_as_admin.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

        # Cleanup
        client_as_admin.delete(f"/api/v1/teams/{team_id}")

    def test_regular_user_can_read_teams(
        self, client_as_admin: TestClient, client_as_user: TestClient
    ):
        """Test that regular users can read but not modify teams."""
        # Admin creates a team
        create_payload = {
            "name": "Read Only Club",
            "team_type": "club",
            "sanctioning_body": "USA Swimming",
            "lsc": "ME",
        }
        response = client_as_admin.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 201
        team_id = response.json()["id"]

        # Regular user can GET
        response = client_as_user.get(f"/api/v1/teams/{team_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Read Only Club"

        # Regular user can LIST
        response = client_as_user.get("/api/v1/teams")
        assert response.status_code == 200

        # Regular user cannot CREATE
        response = client_as_user.post("/api/v1/teams", json=create_payload)
        assert response.status_code == 403

        # Regular user cannot UPDATE
        response = client_as_user.patch(f"/api/v1/teams/{team_id}", json={"name": "Hacked"})
        assert response.status_code == 403

        # Regular user cannot DELETE
        response = client_as_user.delete(f"/api/v1/teams/{team_id}")
        assert response.status_code == 403

        # Cleanup as admin
        client_as_admin.delete(f"/api/v1/teams/{team_id}")
