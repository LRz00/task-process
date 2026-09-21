from pydantic import BaseModel

class TaskCreate(BaseModel):
    user_id: int
    title: str
    description: str
    status: str
    