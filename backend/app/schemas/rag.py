from datetime import datetime

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    doc_id: int
    title: str | None = None
    chunk_id: int
    snippet: str
    score: float


class DocChunkPreview(BaseModel):
    chunk_id: int
    chunk_index: int
    snippet: str


class DocumentViewer(BaseModel):
    doc_id: int
    title: str | None = None
    original_name: str
    mime_type: str
    status: str
    created_at: datetime
    chunks_preview: list[DocChunkPreview]


class DocumentChunkNeighbor(BaseModel):
    chunk_id: int
    chunk_index: int
    snippet: str


class DocumentChunkResponse(BaseModel):
    doc_id: int
    chunk_id: int
    chunk_index: int
    text: str
    snippet: str
    neighbors: list[DocumentChunkNeighbor]


class RagAskRequest(BaseModel):
    question: str = Field(min_length=1)


class RagSource(BaseModel):
    source_no: int
    doc_id: int
    title: str | None = None
    chunk_id: int
    snippet: str


class RagAnswerResponse(BaseModel):
    query_id: int
    version_id: int
    version_no: int
    answer: str
    sources: list[RagSource]


class HistoryItem(BaseModel):
    query_id: int
    question: str
    created_at: datetime
    latest_version_no: int


class HistoryVersion(BaseModel):
    version_id: int
    version_no: int
    answer: str
    created_at: datetime
    sources: list[RagSource]


class HistoryDetail(BaseModel):
    query_id: int
    question: str
    versions: list[HistoryVersion]
