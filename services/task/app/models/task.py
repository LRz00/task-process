from pydantic import BaseModel

class Task(BaseModel):
    user_id: int
    title: str
    description: str
    created_at: str
    updated_at: str
    last_updated_by: str
    shared_with: list[str] = []
    status: str