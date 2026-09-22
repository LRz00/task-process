import os
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from psycopg import OperationalError, connect
from psycopg.errors import ForeignKeyViolation, UniqueViolation
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, field_validator

from app.models.user_create import UserCreate
from app.queries.user_queries import (
    CREATE_USER_GROUP_MEMBERS_TABLE,
    CREATE_USER_GROUP_TABLE,
    INSERT_USER,
    INSERT_USER_GROUP,
    INSERT_USER_GROUP_MEMBERS,
    SELECT_EXISTING_USER_IDS,
    SELECT_HEALTH_CHECK,
    SELECT_USER_BY_ID,
    SELECT_USER_TASKS,
    SELECT_USERS,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://task_user:task_password@localhost:5432/task_db"
)

app = FastAPI()


class UserGroupCreate(BaseModel):
    user_ids: list[int] = Field(min_length=1)

    @field_validator("user_ids")
    @classmethod
    def validate_user_ids(cls, values: list[int]) -> list[int]:
        unique_values = sorted(set(values))
        if len(unique_values) != len(values):
            raise ValueError("user_ids must not contain duplicates")
        if any(user_id <= 0 for user_id in unique_values):
            raise ValueError("user_ids must contain positive integers")
        return unique_values


def _to_iso8601(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _ensure_group_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(CREATE_USER_GROUP_TABLE)
        cur.execute(CREATE_USER_GROUP_MEMBERS_TABLE)


def _assert_users_exist(conn, user_ids: list[int]) -> None:
    with conn.cursor() as cur:
        cur.execute(SELECT_EXISTING_USER_IDS, (user_ids,))
        existing_ids = {row[0] for row in cur.fetchall()}
    missing_ids = [user_id for user_id in user_ids if user_id not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "some users were not found", "missing_user_ids": missing_ids},
        )

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

@app.get("/users")
def list_users():
    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(SELECT_USERS)
                rows = cur.fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "created_at": _to_iso8601(row["created_at"]),
                "updated_at": _to_iso8601(row["updated_at"]),
            }
            for row in rows
        ]
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    INSERT_USER,
                    (user.name, user.email),
                )
                created = cur.fetchone()
        return {
            "id": created["id"],
            "name": created["name"],
            "email": created["email"],
            "created_at": _to_iso8601(created["created_at"]),
            "updated_at": _to_iso8601(created["updated_at"]),
        }
    except UniqueViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already exists",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

@app.get("/users/{user_id}/tasks")
def list_user_tasks(user_id: int):
    if user_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid user_id")

    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(SELECT_USER_BY_ID, (user_id,))
                if cur.fetchone() is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

                cur.execute(
                    SELECT_USER_TASKS,
                    (user_id, user_id),
                )
                rows = cur.fetchall()

        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "last_updated_by": row["last_updated_by"],
                "created_at": _to_iso8601(row["created_at"]),
                "updated_at": _to_iso8601(row["updated_at"]),
                "shared_with": row["shared_with"],
            }
            for row in rows
        ]
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc

@app.post("/users/group", status_code=status.HTTP_201_CREATED)
def create_user_group(payload: UserGroupCreate):
    try:
        with connect(DATABASE_URL, row_factory=dict_row) as conn:
            _ensure_group_tables(conn)
            _assert_users_exist(conn, payload.user_ids)

            with conn.cursor() as cur:
                cur.execute(INSERT_USER_GROUP)
                group_id = cur.fetchone()["id"]

                cur.executemany(
                    INSERT_USER_GROUP_MEMBERS,
                    [(group_id, user_id) for user_id in payload.user_ids],
                )

        return {"group_id": group_id, "user_ids": payload.user_ids}
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid users for group",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc