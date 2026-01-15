from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class TranscriptionRequest(BaseModel):
    filename: Optional[str] = None
    language: Optional[str] = "ru"

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class TranscriptionResponse(BaseModel):
    status: str
    message: str
    transcription_id: str
    filename: str
    text_length: int
    download_url: Optional[str] = None
    external_api_status: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )