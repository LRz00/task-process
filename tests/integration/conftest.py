import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from psycopg import connect
from psycopg.rows import dict_row


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_URL = "postgresql://task_user:task_password@localhost:5432/task_db"


def _load_service_app(service_name: str):
    service_dir = ROOT_DIR / "services" / service_name
    if not service_dir.exists():
        raise RuntimeError(f"service directory not found: {service_dir}")

    # Both services expose package `app`, so unload it before each import.
    for module_name in list(sys.modules.keys()):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    sys.path.insert(0, str(service_dir))
    try:
        module = importlib.import_module("app.main")
        return module.app
    finally:
        sys.path.pop(0)


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL", DEFAULT_DB_URL))


@pytest.fixture(scope="session", autouse=True)
def set_database_env(database_url: str):
    os.environ["DATABASE_URL"] = database_url


@pytest.fixture(scope="session")
def db(database_url: str):
    try:
        with connect(database_url, row_factory=dict_row) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            yield conn
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL is unavailable for integration tests: {exc}")


def _ensure_optional_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_groups (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_group_members (
                group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id),
                PRIMARY KEY (group_id, user_id)
            )
            """
        )


@pytest.fixture(autouse=True)
def clean_database(db):
    _ensure_optional_tables(db)
    with db.cursor() as cur:
        cur.execute(
            """
            TRUNCATE TABLE
                task_shares,
                tasks,
                user_group_members,
                user_groups,
                users
            RESTART IDENTITY CASCADE
            """
        )


@pytest.fixture
def task_client() -> TestClient:
    app = _load_service_app("task")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def user_client() -> TestClient:
    app = _load_service_app("user")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seed_user(db):
    def _seed_user(name: str, email: str) -> dict:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name, email)
                VALUES (%s, %s)
                RETURNING id, name, email
                """,
                (name, email),
            )
            return cur.fetchone()

    return _seed_user


@pytest.fixture
def seed_task(db):
    def _seed_task(user_id: int, title: str, status: str = "pending", description: str | None = None) -> dict:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (user_id, title, description, status, last_updated_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, user_id, title, status
                """,
                (user_id, title, description, status, user_id),
            )
            row = cur.fetchone()
            cur.execute(
                """
                INSERT INTO task_shares (task_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT (task_id, user_id) DO NOTHING
                """,
                (row["id"], user_id),
            )
            return row

    return _seed_task


@pytest.fixture
def share_task_with(db):
    def _share(task_id: int, user_id: int) -> None:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO task_shares (task_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT (task_id, user_id) DO NOTHING
                """,
                (task_id, user_id),
            )

    return _share
