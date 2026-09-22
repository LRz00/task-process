import pytest


pytestmark = pytest.mark.integration


def test_create_task_persists_and_returns_owner_share(task_client, seed_user):
    owner = seed_user("Owner", "owner@example.com")

    response = task_client.post(
        "/tasks",
        json={
            "user_id": owner["id"],
            "title": "Implement integration tests",
            "description": "Using real postgres",
            "status": "pending",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user_id"] == owner["id"]
    assert payload["task"] == "Implement integration tests"
    assert payload["shared_with"] == [owner["id"]]


@pytest.mark.parametrize(
    ("actor_role", "expected_status"),
    [
        ("owner", 200),
        ("shared", 200),
        ("outsider", 403),
    ],
)
def test_update_task_permission_matrix(
    task_client,
    seed_user,
    seed_task,
    share_task_with,
    actor_role,
    expected_status,
):
    owner = seed_user("Owner", "owner@example.com")
    shared_user = seed_user("Shared", "shared@example.com")
    outsider = seed_user("Outsider", "outsider@example.com")
    task = seed_task(owner["id"], "Task for update")
    share_task_with(task["id"], shared_user["id"])

    actor_by_role = {
        "owner": owner["id"],
        "shared": shared_user["id"],
        "outsider": outsider["id"],
    }
    actor_id = actor_by_role[actor_role]

    response = task_client.patch(
        f"/tasks/{task['id']}",
        params={"user_id": actor_id},
        json={"status": "done"},
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        body = response.json()
        assert body["status"] == "done"
        assert body["last_updated_by"] == actor_id


@pytest.mark.parametrize(
    ("owner_actor", "expected_status"),
    [
        (True, 200),
        (False, 403),
    ],
)
def test_share_task_allows_only_owner(task_client, seed_user, seed_task, owner_actor, expected_status):
    owner = seed_user("Owner", "owner@example.com")
    candidate = seed_user("Candidate", "candidate@example.com")
    another_user = seed_user("Another", "another@example.com")
    task = seed_task(owner["id"], "Task for share")

    acting_user_id = owner["id"] if owner_actor else another_user["id"]
    response = task_client.patch(
        f"/tasks/{task['id']}/share",
        json={
            "user_id": acting_user_id,
            "shared_with": [candidate["id"]],
        },
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        body = response.json()
        assert sorted(body["shared_with"]) == sorted([owner["id"], candidate["id"]])
