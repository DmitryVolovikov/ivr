from datetime import datetime

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    id: int
    original_name: str
    mime_type: str
    title: str | None = None
    status: str
    error_reason: str | None = None
    reject_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(DocumentBase):
    pass


class DocumentPublic(BaseModel):
    id: int
    title: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentReject(BaseModel):
    reason: str = Field(min_length=1)
