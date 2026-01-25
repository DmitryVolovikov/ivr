from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_optional_user
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.document import DocumentPublic
from app.schemas.rag import (
    DocumentChunkNeighbor,
    DocumentChunkResponse,
    DocumentViewer,
    DocChunkPreview,
)
from app.services.text_utils import make_snippet

router = APIRouter(prefix="/docs", tags=["documents"])


def _is_admin(user):
    return bool(user and user.is_admin)


@router.get("", response_model=list[DocumentPublic])
def list_published_docs(db: Session = Depends(get_db)) -> list[DocumentPublic]:
    documents = (
        db.query(Document)
        .filter(Document.status == "published")
        .order_by(Document.created_at.desc())
        .all()
    )
    return [DocumentPublic.model_validate(doc) for doc in documents]


@router.get("/{doc_id}", response_model=DocumentViewer)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user()),
) -> DocumentViewer:
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.status != "published" and not _is_admin(user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    preview = [
        DocChunkPreview(
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            snippet=make_snippet(chunk.text),
        )
        for chunk in chunks
    ]
    return DocumentViewer(
        doc_id=document.id,
        title=document.title,
        original_name=document.original_name,
        mime_type=document.mime_type,
        status=document.status,
        created_at=document.created_at,
        chunks_preview=preview,
    )


@router.get("/{doc_id}/chunk/{chunk_id}", response_model=DocumentChunkResponse)
def get_document_chunk(
    doc_id: int,
    chunk_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user()),
) -> DocumentChunkResponse:
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.status != "published" and not _is_admin(user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    chunk = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.id == chunk_id, DocumentChunk.document_id == doc_id)
        .first()
    )
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    neighbors = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == doc_id)
        .filter(
            DocumentChunk.chunk_index.in_(
                [chunk.chunk_index - 1, chunk.chunk_index + 1]
            )
        )
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    neighbor_items = [
        DocumentChunkNeighbor(
            chunk_id=neighbor.id,
            chunk_index=neighbor.chunk_index,
            snippet=make_snippet(neighbor.text),
        )
        for neighbor in neighbors
    ]
    return DocumentChunkResponse(
        doc_id=doc_id,
        chunk_id=chunk.id,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        snippet=make_snippet(chunk.text),
        neighbors=neighbor_items,
    )


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user()),
) -> FileResponse:
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.status != "published" and not _is_admin(user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    path = Path(document.stored_filename)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(path, media_type=document.mime_type, filename=document.original_name)
