import os
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, status
from psycopg import OperationalError, connect
from psycopg.errors import ForeignKeyViolation
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, field_validator

from app.models.task_create import TaskCreate
from app.models.task_update import TaskUpdate
from app.queries.task_queries import (
    INSERT_TASK,
    INSERT_TASK_SHARE,
    SELECT_EXISTING_USER_IDS,
    SELECT_HEALTH_CHECK,
    SELECT_TASKS,
    SELECT_TASK_WITH_SHARES,
    SELECT_USER_BY_ID,
    UPDATE_TASK,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://task_user:task_password@localhost:5432/task_db"
)

app = FastAPI(title="Task Service")


class TaskShareUpdate(BaseModel):
    user_id: int = Field(gt=0)
    shared_with: list[int] = Field(min_length=1)

    @field_validator("shared_with")
    @classmethod
    def validate_shared_with(cls, values: list[int]) -> list[int]:
        unique_values = sorted(set(values))
        if len(unique_values) != len(values):
            raise ValueError("shared_with must not contain duplicates")
        if any(item <= 0 for item in unique_values):
            raise ValueError("shared_with must contain positive integers")
        return unique_values


def _to_iso8601(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _assert_user_exists(conn, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(SELECT_USER_BY_ID, (user_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")


def _assert_users_exist(conn, user_ids: list[int]) -> None:
    with conn.cursor() as cur:
        cur.execute(SELECT_EXISTING_USER_IDS, (user_ids,))
        existing_ids = {row[0] for row in cur.fetchall()}
    missing = [user_id for user_id in user_ids if user_id not in existing_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "some users were not found", "missing_user_ids": missing},
        )


def _fetch_task_with_shares(conn, task_id: int):
    with conn.cursor() as cur:
        cur.execute(SELECT_TASK_WITH_SHARES, (task_id,))
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return row


def _serialize_task(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "task": row["title"],
        "description": row["description"],
        "status": row["status"],
        "created_at": _to_iso8601(row["created_at"]),
        "updated_at": _to_iso8601(row["updated_at"]),
        "last_updated_by": row["last_updated_by"],
        "shared_with": row["shared_with"],
    }

@app.get("/health")
def health():
    try:
        with connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(SELECT_HEALTH_CHECK)
                cur.fetchone()
        database = "connected"
    except OperationalError:
        database = "disconnected"
    return {"status": "OK", "database": database}

@app.get("/tasks")
def list_tasks():
    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(SELECT_TASKS)
                rows = cur.fetchall()
        return [_serialize_task(row) for row in rows]
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            _assert_user_exists(conn, task.user_id)

            with conn.cursor() as cur:
                cur.execute(
                    INSERT_TASK,
                    (
                        task.user_id,
                        task.title,
                        task.description,
                        task.status,
                        task.user_id,
                    ),
                )
                task_id = cur.fetchone()["id"]

                cur.execute(
                    INSERT_TASK_SHARE,
                    (task_id, task.user_id),
                )

            created_task = _fetch_task_with_shares(conn, task_id)

        return _serialize_task(created_task)
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid task reference",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, user_id: int = Query(gt=0)):
    if task_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid task_id")

    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            _assert_user_exists(conn, user_id)
            current_task = _fetch_task_with_shares(conn, task_id)

            if user_id != current_task["user_id"] and user_id not in current_task["shared_with"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="user does not have permission to update this task",
                )

            with conn.cursor() as cur:
                cur.execute(
                    UPDATE_TASK,
                    (
                        task.title,
                        task.description,
                        task.status,
                        user_id,
                        task_id,
                    ),
                )
                if cur.fetchone() is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")

            updated_task = _fetch_task_with_shares(conn, task_id)

        return _serialize_task(updated_task)
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid task update",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

@app.patch("/tasks/{task_id}/share")
def share_task(task_id: int, payload: TaskShareUpdate):
    if task_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid task_id")

    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            _assert_user_exists(conn, payload.user_id)
            _assert_users_exist(conn, payload.shared_with)
            task_row = _fetch_task_with_shares(conn, task_id)

            if task_row["user_id"] != payload.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="only task owner can share the task",
                )

            with conn.cursor() as cur:
                cur.executemany(
                    INSERT_TASK_SHARE,
                    [(task_id, shared_user_id) for shared_user_id in payload.shared_with],
                )

            shared_task = _fetch_task_with_shares(conn, task_id)

        return _serialize_task(shared_task)
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid task share payload",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc