from pydantic import BaseModel, Field, field_validator


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
