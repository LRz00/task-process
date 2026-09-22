from typing import Literal

from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: Literal["pending", "in_progress", "done"] = "pending"
    