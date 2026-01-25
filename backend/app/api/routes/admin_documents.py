import shutil
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Response
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_db
from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.document import DocumentReject, DocumentResponse
from pypdf.errors import PdfReadError

from app.services.document_processing import chunk_text, extract_text_from_file, normalize_text
from app.services.retrieval import mark_index_dirty
from app.services.storage import ensure_storage_dirs

router = APIRouter(prefix="/admin/documents", tags=["admin-documents"])
logger = logging.getLogger(__name__)


def _save_upload(file):
    ensure_storage_dirs()
    extension = Path(file.filename or "").suffix
    stored_name = f"{uuid4().hex}{extension}"
    full_path = Path(settings.docs_path) / stored_name
    with full_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)
    return full_path


def _process_document(db, document, path):
    text = extract_text_from_file(path, document.mime_type)
    normalized = normalize_text(text)
    if not normalized:
        raise ValueError("Extracted text is empty")
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    chunks = [
        DocumentChunk(document_id=document.id, chunk_index=index, text=chunk)
        for index, chunk in enumerate(chunk_text(normalized))
    ]
    if not chunks:
        raise ValueError("No chunks generated")
    db.add_all(chunks)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> DocumentResponse:
    stored_path = _save_upload(file)
    document = Document(
        original_name=file.filename or stored_path.name,
        stored_filename=str(stored_path),
        mime_type=file.content_type or "application/octet-stream",
        title=title,
        status="indexing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    mark_index_dirty()

    try:
        _process_document(db, document, stored_path)
        document.status = "review"
        document.error_reason = None
        document.reject_reason = None
    except (ValueError, OSError, PdfReadError) as exc:
        document.status = "error"
        document.error_reason = str(exc)
        logger.warning(
            "Failed to process uploaded document doc_id=%s error=%s",
            document.id,
            exc,
        )
    db.add(document)
    db.commit()
    db.refresh(document)
    mark_index_dirty()
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> list[DocumentResponse]:
    query = db.query(Document)
    if status:
        query = query.filter(Document.status == status)
    documents = query.order_by(Document.created_at.desc()).all()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.post("/{doc_id}/publish", response_model=DocumentResponse)
def publish_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> DocumentResponse:
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.status = "published"
    document.reject_reason = None
    document.error_reason = None
    db.add(document)
    db.commit()
    db.refresh(document)
    mark_index_dirty()
    return DocumentResponse.model_validate(document)


@router.post("/{doc_id}/reject", response_model=DocumentResponse)
def reject_document(
    doc_id: int,
    payload: DocumentReject,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> DocumentResponse:
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.status = "rejected"
    document.reject_reason = payload.reason
    db.add(document)
    db.commit()
    db.refresh(document)
    mark_index_dirty()
    return DocumentResponse.model_validate(document)


@router.post("/{doc_id}/reindex", response_model=DocumentResponse)
def reindex_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> DocumentResponse:
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.status = "indexing"
    document.error_reason = None
    document.reject_reason = None
    db.add(document)
    db.commit()
    db.refresh(document)

    path = Path(document.stored_filename)
    try:
        _process_document(db, document, path)
        document.status = "review"
    except (ValueError, OSError, PdfReadError) as exc:
        document.status = "error"
        document.error_reason = str(exc)
        logger.warning(
            "Failed to reindex document doc_id=%s error=%s",
            document.id,
            exc,
        )
    db.add(document)
    db.commit()
    db.refresh(document)
    mark_index_dirty()
    return DocumentResponse.model_validate(document)


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> Response:
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    stored_path = Path(document.stored_filename)
    db.delete(document)
    db.commit()

    try:
        stored_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed to delete document file doc_id=%s error=%s", document.id, exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
