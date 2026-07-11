"""Request/response models for ingestion endpoints."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    handle: str
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    handle: str
    source: str
    status: str                 # queued | parsing | enriching | analyzing | complete | failed
    step: str | None = None
    queue_position: int = 0     # 0 = running/next; N = N ahead in line
    films_total: int
    films_processed: int
    films_matched: int
    films_unmatched: int
    error_code: str | None = None
    error_message: str | None = None
