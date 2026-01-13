"""Integration test for recording a real swim time with all related entities."""

import pytest
from fastapi.testclient import TestClient

from swimcuttimes.config import get_settings

# Skip tests if service_role key is not configured (RLS blocks operations)
pytestmark = pytest.mark.skipif(
    get_settings().supabase_service_role_key is None,
    reason="SUPABASE_SERVICE_ROLE_KEY not configured - tests require service role to bypass RLS",
)

# Event ID for 50 Freestyle SCY (seeded in database)
EVENT_50_FREE_SCY = "zhbmz7saxidk"


class TestRecordSwimTime:
    """Integration test: create swimmer, team, meet, and record a time."""

    def test_record_elise_drake_frosty_frenzy(self, client_as_admin: TestClient):
        """
        Record Elise Drake's 50 Free time at NE CRIM Frosty Frenzy.

        Meet: NE CRIM FROSTY FRENZY
        Date: Dec 12-14, 2025
        Location: WPI Sports and Recreation Center, Worcester, MA
        Course: SCY

        Swimmer: Elise Drake
        Team: Greenwood Swimming (MA)

        Event: 50 Free Prelims (15+)
        Time: 25.94
        Place: 3
        """
        # =====================================================================
        # 1. Create Team: Greenwood Swimming (MA)
        # =====================================================================
        team_payload = {
            "name": "Greenwood Swimming",
            "team_type": "club",
            "sanctioning_body": "USA Swimming",
            "lsc": "NE",
            "state": "MA",
            "country": "USA",
        }
        response = client_as_admin.post("/api/v1/teams", json=team_payload)
        assert response.status_code == 201, f"Failed to create team: {response.text}"
        team = response.json()
        team_id = team["id"]
        assert team["name"] == "Greenwood Swimming"
        assert team["lsc"] == "NE"

        try:
            # =================================================================
            # 2. Create Swimmer: Elise Drake
            # =================================================================
            # Assuming she's 15+ based on age group, use a birth date that makes her 16
            swimmer_payload = {
                "first_name": "Elise",
                "last_name": "Drake",
                "date_of_birth": "2009-06-15",  # ~16 years old at time of meet
                "gender": "F",
            }
            response = client_as_admin.post("/api/v1/swimmers", json=swimmer_payload)
            assert response.status_code == 201, f"Failed to create swimmer: {response.text}"
            swimmer = response.json()
            swimmer_id = swimmer["id"]
            assert swimmer["first_name"] == "Elise"
            assert swimmer["last_name"] == "Drake"

            try:
                # =============================================================
                # 3. Assign Swimmer to Team
                # =============================================================
                assignment_payload = {
                    "team_id": team_id,
                    "start_date": "2024-09-01",
                }
                response = client_as_admin.post(
                    f"/api/v1/swimmers/{swimmer_id}/teams", json=assignment_payload
                )
                assert response.status_code == 201, f"Failed to assign team: {response.text}"

                # =============================================================
                # 4. Create Meet: NE CRIM FROSTY FRENZY
                # =============================================================
                meet_payload = {
                    "name": "NE CRIM FROSTY FRENZY",
                    "location": "WPI Sports and Recreation Center",
                    "city": "Worcester",
                    "state": "MA",
                    "country": "USA",
                    "start_date": "2025-12-12",
                    "end_date": "2025-12-14",
                    "course": "scy",
                    "lanes": 8,
                    "indoor": True,
                    "sanctioning_body": "USA Swimming",
                    "meet_type": "invitational",
                }
                response = client_as_admin.post("/api/v1/meets", json=meet_payload)
                assert response.status_code == 201, f"Failed to create meet: {response.text}"
                meet = response.json()
                meet_id = meet["id"]
                assert meet["name"] == "NE CRIM FROSTY FRENZY"
                assert meet["course"] == "scy"

                try:
                    # =========================================================
                    # 5. Record Time: 50 Free Prelims, 25.94, Place 3
                    # =========================================================
                    time_payload = {
                        "swimmer_id": swimmer_id,
                        "event_id": EVENT_50_FREE_SCY,
                        "meet_id": meet_id,
                        "team_id": team_id,
                        "time_centiseconds": 2594,  # 25.94 seconds
                        "swim_date": "2025-12-12",
                        "round": "prelims",
                        "place": 3,
                        "official": True,
                        "dq": False,
                    }
                    response = client_as_admin.post("/api/v1/times", json=time_payload)

                    # Check if event exists
                    if response.status_code == 500 and "foreign key" in response.text.lower():
                        pytest.skip("50 Free SCY event not seeded in database")

                    assert response.status_code == 201, f"Failed to create time: {response.text}"
                    time_data = response.json()
                    time_id = time_data["id"]

                    # Verify the recorded time
                    assert time_data["swimmer_id"] == swimmer_id
                    assert time_data["event_id"] == EVENT_50_FREE_SCY
                    assert time_data["meet_id"] == meet_id
                    assert time_data["team_id"] == team_id
                    assert time_data["time_centiseconds"] == 2594
                    assert time_data["time_formatted"] == "25.94"
                    assert time_data["round"] == "prelims"
                    assert time_data["place"] == 3
                    assert time_data["official"] is True
                    assert time_data["dq"] is False

                    # =========================================================
                    # 6. Verify: Query the time back
                    # =========================================================
                    response = client_as_admin.get(f"/api/v1/times/{time_id}")
                    assert response.status_code == 200
                    fetched_time = response.json()
                    assert fetched_time["time_formatted"] == "25.94"

                    # Query times by swimmer
                    response = client_as_admin.get(
                        "/api/v1/times", params={"swimmer_id": swimmer_id}
                    )
                    assert response.status_code == 200
                    times = response.json()
                    assert len(times) >= 1
                    assert any(t["id"] == time_id for t in times)

                    # Query times by meet
                    response = client_as_admin.get(
                        "/api/v1/times", params={"meet_id": meet_id}
                    )
                    assert response.status_code == 200
                    times = response.json()
                    assert len(times) >= 1
                    assert any(t["id"] == time_id for t in times)

                    # Cleanup time
                    client_as_admin.delete(f"/api/v1/times/{time_id}")

                finally:
                    # Cleanup meet
                    client_as_admin.delete(f"/api/v1/meets/{meet_id}")

            finally:
                # Cleanup swimmer
                client_as_admin.delete(f"/api/v1/swimmers/{swimmer_id}")

        finally:
            # Cleanup team
            client_as_admin.delete(f"/api/v1/teams/{team_id}")
