import pytest


pytestmark = pytest.mark.integration


def test_create_user_persists_record(user_client):
    response = user_client.post(
        "/users",
        json={"name": "Alice", "email": "alice@example.com"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alice"
    assert body["email"] == "alice@example.com"
    assert body["id"] > 0


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "email": "valid@example.com"},
        {"name": "A", "email": "valid@example.com"},
        {"name": "Valid User", "email": "invalid-email"},
    ],
)
def test_create_user_rejects_invalid_payload(user_client, payload):
    response = user_client.post("/users", json=payload)
    assert response.status_code == 422


def test_list_user_tasks_returns_owned_and_shared(user_client, seed_user, seed_task, share_task_with):
    owner = seed_user("Owner", "owner@example.com")
    viewer = seed_user("Viewer", "viewer@example.com")

    owned_task = seed_task(viewer["id"], "Owned by viewer")
    shared_task = seed_task(owner["id"], "Shared with viewer")
    share_task_with(shared_task["id"], viewer["id"])

    response = user_client.get(f"/users/{viewer['id']}/tasks")

    assert response.status_code == 200
    body = response.json()
    returned_ids = [item["id"] for item in body]
    assert returned_ids == [owned_task["id"], shared_task["id"]]


@pytest.mark.parametrize(
    "user_ids, expected_status",
    [
        ([1, 2], 201),
        ([1, 999], 404),
    ],
)
def test_create_user_group_success_and_missing_users(
    user_client,
    seed_user,
    user_ids,
    expected_status,
):
    first = seed_user("User One", "one@example.com")
    second = seed_user("User Two", "two@example.com")
    ids_map = {1: first["id"], 2: second["id"], 999: 999}
    payload_ids = [ids_map[item] for item in user_ids]

    response = user_client.post(
        "/users/group",
        json={"user_ids": payload_ids},
    )

    assert response.status_code == expected_status
    if expected_status == 201:
        body = response.json()
        assert body["user_ids"] == payload_ids