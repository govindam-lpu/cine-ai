from typing import Any

from pydantic import BaseModel


class ErrorPayload(BaseModel):
    code: str
    message: str


class Envelope(BaseModel):
    success: bool
    data: Any = None
    error: ErrorPayload | None = None
