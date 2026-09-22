from typing import Literal

from pydantic import BaseModel, Field, model_validator

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: Literal["pending", "in_progress", "done"] | None = None

    @model_validator(mode="after")
    def validate_has_changes(self) -> "TaskUpdate":
        if self.title is None and self.description is None and self.status is None:
            raise ValueError("at least one field must be provided")
        return self