import copy
import pytest
from fastapi.testclient import TestClient
import src.app as app_module


ORIGINAL_ACTIVITIES = copy.deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def reset_activities():
    app_module.activities = copy.deepcopy(ORIGINAL_ACTIVITIES)
    yield
    app_module.activities = copy.deepcopy(ORIGINAL_ACTIVITIES)


@pytest.fixture
def client():
    return TestClient(app_module.app)


class TestRoot:
    def test_redirects_to_static_index(self, client):
        expected_location = "/static/index.html"
        expected_status = 307

        response = client.get("/", follow_redirects=False)

        assert response.status_code == expected_status
        assert response.headers["location"] == expected_location


class TestGetActivities:
    def test_returns_all_activities(self, client):
        expected_count = 9
        expected_type = dict

        response = client.get("/activities")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, expected_type)
        assert len(data) == expected_count

    def test_activity_schema(self, client):
        expected_keys = {"description", "schedule", "max_participants", "participants"}

        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]

        assert expected_keys.issubset(activity.keys())
        assert isinstance(activity["participants"], list)

    def test_initial_participants_present(self, client):
        chess_participants = ["michael@mergington.edu", "daniel@mergington.edu"]
        programming_participants = ["emma@mergington.edu", "sophia@mergington.edu"]

        response = client.get("/activities")
        data = response.json()

        for participant in chess_participants:
            assert participant in data["Chess Club"]["participants"]
        for participant in programming_participants:
            assert participant in data["Programming Class"]["participants"]


class TestSignup:
    def test_signup_success(self, client):
        activity_name = "Basketball Team"
        email = "newstudent@mergington.edu"

        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        assert response.status_code == 200
        assert f"Signed up {email} for {activity_name}" in response.json()["message"]

        response = client.get("/activities")
        data = response.json()
        assert email in data[activity_name]["participants"]

    def test_signup_duplicate_returns_400(self, client):
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        expected_detail = "Student already signed up for this activity"

        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == expected_detail

    def test_signup_nonexistent_activity_returns_404(self, client):
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"
        expected_detail = "Activity not found"

        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == expected_detail

    def test_signup_increases_participant_count(self, client):
        activity_name = "Basketball Team"
        email = "player@mergington.edu"

        response = client.get("/activities")
        initial_count = len(response.json()[activity_name]["participants"])

        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        response = client.get("/activities")
        new_count = len(response.json()[activity_name]["participants"])

        assert new_count == initial_count + 1


class TestRemoveParticipant:
    def test_remove_success(self, client):
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        expected_message = f"Removed {email} from {activity_name}"

        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )

        assert response.status_code == 200
        assert response.json()["message"] == expected_message

        response = client.get("/activities")
        assert email not in response.json()[activity_name]["participants"]

    def test_remove_nonexistent_participant_returns_404(self, client):
        activity_name = "Chess Club"
        email = "notregistered@mergington.edu"
        expected_detail = "Student not found in this activity"

        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == expected_detail

    def test_remove_nonexistent_activity_returns_404(self, client):
        activity_name = "Nonexistent Club"
        email = "student@mergington.edu"
        expected_detail = "Activity not found"

        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == expected_detail

    def test_remove_decreases_participant_count(self, client):
        activity_name = "Chess Club"
        email = "michael@mergington.edu"

        response = client.get("/activities")
        initial_count = len(response.json()[activity_name]["participants"])

        client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )

        response = client.get("/activities")
        new_count = len(response.json()[activity_name]["participants"])

        assert new_count == initial_count - 1


class TestActivityCapacity:
    def test_signup_respects_max_participants(self, client):
        activity_name = "Gym Class"
        max_participants = 30

        response = client.get("/activities")
        current_count = len(response.json()[activity_name]["participants"])
        new_emails = [f"student{i}@mergington.edu" for i in range(max_participants - current_count)]

        for email in new_emails:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        overflow_email = "overflow@mergington.edu"
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": overflow_email}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Activity is full"
