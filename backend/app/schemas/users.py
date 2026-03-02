from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    letterboxd_username: str
    serializd_username: str | None = None
    country_code: str = Field(default="US", min_length=2, max_length=2)
    preferred_format: str = Field(default="both")


class PatchUserRequest(BaseModel):
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    preferred_format: str | None = None
    display_name: str | None = None
