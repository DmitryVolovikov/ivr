from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query as FastAPIQuery, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.document import Document, DocumentChunk
from app.models.query import Citation, Query, QueryVersion
from app.models.user import User
from app.schemas.rag import RagAnswerResponse, RagAskRequest, RagSource
from app.core.config import settings
from app.services.llm import LLMResult, SourceItem, generate_answer_with_meta
from app.services.retrieval import search_chunks_with_meta
from app.services.text_utils import make_llm_excerpt, make_snippet

router = APIRouter(prefix="/rag", tags=["rag"])

logger = logging.getLogger(__name__)


def _build_sources(
    db: Session,
    hits: list[tuple[int, float]],
    *,
    query: str,
) -> tuple[list[RagSource], list[float], list[str]]:
    if not hits:
        return [], [], []
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
    sources: list[RagSource] = []
    scores: list[float] = []
    llm_excerpts: list[str] = []
    for idx, (chunk_id, score) in enumerate(hits, start=1):
        mapped = chunk_map.get(chunk_id)
        if not mapped:
            continue
        chunk, doc_id, title = mapped
        llm_excerpts.append(
            make_llm_excerpt(
                chunk.text,
                query=query,
                max_length=settings.llm_excerpt_chars,
            )
        )
        sources.append(
            RagSource(
                source_no=idx,
                doc_id=doc_id,
                title=title,
                chunk_id=chunk.id,
                snippet=make_snippet(chunk.text, query=query),
            )
        )
        scores.append(score)
    return sources, scores, llm_excerpts


def _generate_answer(
    question: str,
    sources: list[RagSource],
    scores: list[float] | None,
    llm_excerpts: list[str],
) -> tuple[str, list[RagSource], LLMResult]:
    llm_sources = [
        SourceItem(
            source.source_no,
            source.snippet,
            score=scores[idx] if scores and idx < len(scores) else None,
            title=source.title,
            chunk_id=source.chunk_id,
            llm_excerpt=llm_excerpts[idx] if idx < len(llm_excerpts) else None,
        )
        for idx, source in enumerate(sources)
    ]
    result = generate_answer_with_meta(question, llm_sources)
    if not sources:
        return result.answer, [], result
    if result.error:
        fallback = LLMResult(
            answer=result.answer,
            provider=result.provider,
            model=result.model,
            error=result.error,
        )
        return fallback.answer, sources, fallback
    return result.answer, sources, result


def _store_citations(
    db: Session,
    version: QueryVersion,
    sources: list[RagSource],
) -> int:
    if not sources:
        return 0
    chunk_ids = {source.chunk_id for source in sources}
    existing_chunk_ids = {
        chunk_id
        for (chunk_id,) in db.query(DocumentChunk.id)
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    }
    valid_sources = [source for source in sources if source.chunk_id in existing_chunk_ids]
    skipped_count = len(sources) - len(valid_sources)
    citations = [
        Citation(
            query_version_id=version.id,
            source_no=source.source_no,
            document_id=source.doc_id,
            chunk_id=source.chunk_id,
            snippet=source.snippet,
        )
        for source in valid_sources
    ]
    if citations:
        db.add_all(citations)
    return skipped_count


def _apply_diagnostics(
    response: Response,
    llm_result: LLMResult,
    retriever: str,
) -> None:
    response.headers["X-LLM-Provider"] = llm_result.provider
    response.headers["X-LLM-Model"] = llm_result.model
    response.headers["X-Retriever"] = retriever
    if llm_result.error:
        response.headers["X-Ollama-Error"] = llm_result.error


@router.post("/ask", response_model=RagAnswerResponse)
def ask_question(
    payload: RagAskRequest,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user()),
) -> RagAnswerResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    hits, retriever = search_chunks_with_meta(
        db,
        question,
        limit=settings.retrieve_k_for_llm,
    )
    sources, scores, llm_excerpts = _build_sources(db, hits, query=question)
    answer, final_sources, llm_result = _generate_answer(
        question,
        sources,
        scores,
        llm_excerpts,
    )
    ui_sources = final_sources[: settings.ui_sources_k]

    query = Query(user_id=user.id, question=question)
    db.add(query)
    db.commit()
    db.refresh(query)

    version = QueryVersion(query_id=query.id, version_no=1, answer=answer)
    db.add(version)
    db.commit()
    db.refresh(version)

    if ui_sources:
        skipped_count = _store_citations(db, version, ui_sources)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.warning(
                "Failed to store citations for query_version_id=%s skipped_count=%s",
                version.id,
                skipped_count,
            )

    if llm_result.error:
        logger.warning(
            "RAG answer fallback used query_id=%s user_id=%s error=%s",
            query.id,
            user.id,
            llm_result.error,
        )

    _apply_diagnostics(response, llm_result, retriever)
    return RagAnswerResponse(
        query_id=query.id,
        version_id=version.id,
        version_no=version.version_no,
        answer=answer,
        sources=ui_sources,
    )


def _rerun_question(
    query_id: int,
    response: Response,
    db: Session,
    user: User,
) -> RagAnswerResponse:
    query = db.query(Query).filter(Query.id == query_id).first()
    if query is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")
    if query.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    latest_version = (
        db.query(func.max(QueryVersion.version_no))
        .filter(QueryVersion.query_id == query.id)
        .scalar()
    )
    next_version_no = int(latest_version or 0) + 1

    hits, retriever = search_chunks_with_meta(
        db,
        query.question,
        limit=settings.retrieve_k_for_llm,
    )
    sources, scores, llm_excerpts = _build_sources(db, hits, query=query.question)
    answer, final_sources, llm_result = _generate_answer(
        query.question,
        sources,
        scores,
        llm_excerpts,
    )
    ui_sources = final_sources[: settings.ui_sources_k]

    version = QueryVersion(query_id=query.id, version_no=next_version_no, answer=answer)
    db.add(version)
    db.commit()
    db.refresh(version)

    if ui_sources:
        skipped_count = _store_citations(db, version, ui_sources)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.warning(
                "Failed to store citations for query_version_id=%s skipped_count=%s",
                version.id,
                skipped_count,
            )

    if llm_result.error:
        logger.warning(
            "RAG rerun fallback used query_id=%s user_id=%s error=%s",
            query.id,
            user.id,
            llm_result.error,
        )

    _apply_diagnostics(response, llm_result, retriever)
    return RagAnswerResponse(
        query_id=query.id,
        version_id=version.id,
        version_no=version.version_no,
        answer=answer,
        sources=ui_sources,
    )


@router.post("/rerun", response_model=RagAnswerResponse)
def rerun_question_by_query(
    response: Response,
    query_id: int = FastAPIQuery(..., alias="query_id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user()),
) -> RagAnswerResponse:
    return _rerun_question(query_id, response, db, user)


@router.post("/ask/{query_id}/rerun", response_model=RagAnswerResponse)
def rerun_question(
    query_id: int,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user()),
) -> RagAnswerResponse:
    return _rerun_question(query_id, response, db, user)
