from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.models.query import Citation, Query, QueryVersion
from app.models.user import User
from app.schemas.rag import HistoryDetail, HistoryItem, HistoryVersion, RagSource

router = APIRouter(tags=["history"])


@router.get("/history", response_model=list[HistoryItem])
def list_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user()),
) -> list[HistoryItem]:
    latest_version_subq = (
        db.query(
            QueryVersion.query_id,
            func.max(QueryVersion.version_no).label("latest_version_no"),
        )
        .group_by(QueryVersion.query_id)
        .subquery()
    )
    query = (
        db.query(Query, latest_version_subq.c.latest_version_no)
        .outerjoin(latest_version_subq, Query.id == latest_version_subq.c.query_id)
        .order_by(Query.created_at.desc())
    )
    if not user.is_admin:
        query = query.filter(Query.user_id == user.id)
    rows = query.limit(limit).all()
    return [
        HistoryItem(
            query_id=record.id,
            question=record.question,
            created_at=record.created_at,
            latest_version_no=int(latest_version or 0),
        )
        for record, latest_version in rows
    ]


@router.get("/history/{query_id}", response_model=HistoryDetail)
def get_history_detail(
    query_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user()),
) -> HistoryDetail:
    query = db.query(Query).filter(Query.id == query_id).first()
    if query is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")
    if query.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    versions = (
        db.query(QueryVersion)
        .filter(QueryVersion.query_id == query.id)
        .order_by(QueryVersion.version_no.asc())
        .all()
    )
    version_ids = [version.id for version in versions]
    citations = (
        db.query(Citation)
        .filter(Citation.query_version_id.in_(version_ids))
        .order_by(Citation.source_no.asc())
        .all()
        if version_ids
        else []
    )
    doc_ids = {citation.document_id for citation in citations}
    doc_titles = {
        doc.id: doc.title
        for doc in db.query(Document).filter(Document.id.in_(doc_ids)).all()
    }
    citation_map: dict[int, list[RagSource]] = {}
    for citation in citations:
        citation_map.setdefault(citation.query_version_id, []).append(
            RagSource(
                source_no=citation.source_no,
                doc_id=citation.document_id,
                title=doc_titles.get(citation.document_id),
                chunk_id=citation.chunk_id,
                snippet=citation.snippet,
            )
        )

    version_items = [
        HistoryVersion(
            version_id=version.id,
            version_no=version.version_no,
            answer=version.answer,
            created_at=version.created_at,
            sources=citation_map.get(version.id, []),
        )
        for version in versions
    ]
    return HistoryDetail(
        query_id=query.id,
        question=query.question,
        versions=version_items,
    )
