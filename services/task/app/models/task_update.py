from pydantic import BaseModel

class TaskUpdate(BaseModel):
    title: str
    description: str
    status: str
    updated_at: str
    last_updated_by: str
    shared_with: list[str] = []