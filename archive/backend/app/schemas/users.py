from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    letterboxd_username: str
    country_code: str = Field(default="US", min_length=2, max_length=2)
    preferred_format: str = Field(default="both")
