import os

from fastapi import FastAPI
from psycopg import OperationalError, connect

from app.models.task_create import TaskCreate
from app.models.task_update import TaskUpdate

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://task_user:task_password@localhost:5432/task_db"
)

app = FastAPI(title="Task Service")

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

@app.get("/tasks")
def list_tasks():
    return []

@app.post("/tasks")
def create_task(task: TaskCreate):
    return {"task": task.title, 
            "description": task.description,
            "user_id": task.user_id, 
            "status": "pending",
            "created_at": "2024-06-01T12:00:00Z",
            "updated_at": "2024-06-01T12:00:00Z",
            "last_updated_by": task.user_id,
            "shared_with": [task.user_id]
            }

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, user_id: int):
    return {"task_id": task_id, 
            "task": task.title, 
            "description": task.description,
            "status": task.status,
            "created_at": "2024-06-01T12:00:00Z",
            "updated_at": "2024-06-01T12:00:00Z",
            "last_updated_by": user_id,
            "shared_with": [user_id],
            "user_id": user_id, "status": "updated"}

@app.patch("/tasks/{task_id}/share")
def share_task(task_id: int, user_id: int, shared_with: list[int]):
    return {"task_id": task_id, 
            "user_id": user_id, 
            "shared_with": shared_with}