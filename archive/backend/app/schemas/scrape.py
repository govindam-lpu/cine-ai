from pydantic import BaseModel


class ScrapeRequest(BaseModel):
    user_id: str
    mode: str = "full"
