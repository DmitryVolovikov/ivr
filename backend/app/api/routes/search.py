from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.document import Document, DocumentChunk
from app.schemas.rag import SearchResult
from app.services.retrieval import search_chunks
from app.services.text_utils import make_snippet

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchResult])
def search_documents(
    q: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user()),
) -> list[SearchResult]:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    hits = search_chunks(db, query, limit)
    if not hits:
        return []

    chunk_ids = [chunk_id for chunk_id, _ in hits]
    rows = (
        db.query(DocumentChunk, Document.id, Document.title)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.status == "published")
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )
    chunk_map = {
        chunk.id: (chunk, doc_id, title) for chunk, doc_id, title in rows
    }

    results: list[SearchResult] = []
    for chunk_id, score in hits:
        mapped = chunk_map.get(chunk_id)
        if not mapped:
            continue
        chunk, doc_id, title = mapped
        results.append(
            SearchResult(
                doc_id=doc_id,
                title=title,
                chunk_id=chunk.id,
                snippet=make_snippet(chunk.text, query=query),
                score=score,
            )
        )
    return results
