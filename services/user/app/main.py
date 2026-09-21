import os

from fastapi import FastAPI
from psycopg import OperationalError, connect

from app.models.user_create import UserCreate

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://task_user:task_password@localhost:5432/task_db"
)

app = FastAPI()

@app.get("/health")
def health():
    try:
        with connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        database = "connected"
    except OperationalError:
        database = "disconnected"
    return {"status": "OK", "database": database}

@app.get("/users")
def list_users():
    return []

@app.post("/users")
def create_user(user: UserCreate):
    return {"id": 1, "name": user.name, "email": user.email}