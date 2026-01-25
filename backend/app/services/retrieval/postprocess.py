from __future__ import annotations

from typing import Any, Callable, Iterable

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.retrieval.rrf import sort_hits


def neighbor_lookup(db: Session, *, neighbors_window: int) -> Callable[[int, int], list[DocumentChunk]]:
    def _lookup(doc_id: int, chunk_index: int) -> list[DocumentChunk]:
        return (
            db.query(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.status == "published")
            .filter(DocumentChunk.document_id == doc_id)
            .filter(
                DocumentChunk.chunk_index.between(
                    chunk_index - neighbors_window, chunk_index + neighbors_window
                )
            )
            .all()
        )

    return _lookup


def _neighbor_penalty(delta: int) -> float:
    distance = abs(delta)
    if distance <= 0:
        return 1.0
    if distance == 1:
        return 0.85
    if distance == 2:
        return 0.75
    return 0.65


def expand_neighbors_with_lookup(
    fused: list[tuple[int, float]],
    meta: list[dict[str, int]],
    *,
    seed_n: int,
    neighbors_window: int,
    neighbor_lookup: Callable[[int, int], Iterable[Any]],
) -> tuple[list[tuple[int, float]], int, int, int]:
    if not fused:
        return fused, 0, 0, 0
    seed_n = min(seed_n, len(fused))
    chunk_id_to_pos = {item["chunk_id"]: idx for idx, item in enumerate(meta)}
    scores_by_chunk_id: dict[int, float] = {}
    for idx, score in fused:
        chunk_id = meta[idx]["chunk_id"]
        scores_by_chunk_id[chunk_id] = score
    neighbors_added = 0
    for idx, score in fused[:seed_n]:
        item = meta[idx]
        doc_id = item["doc_id"]
        chunk_index = item["chunk_index"]
        for neighbor in neighbor_lookup(doc_id, chunk_index):
            delta = neighbor.chunk_index - chunk_index
            if delta == 0 or abs(delta) > neighbors_window:
                continue
            neighbor_score = score * _neighbor_penalty(delta)
            existing = scores_by_chunk_id.get(neighbor.id)
            if existing is None:
                scores_by_chunk_id[neighbor.id] = neighbor_score
                neighbors_added += 1
            elif neighbor_score > existing:
                scores_by_chunk_id[neighbor.id] = neighbor_score
    expanded_hits = [
        (chunk_id_to_pos[chunk_id], score)
        for chunk_id, score in scores_by_chunk_id.items()
        if chunk_id in chunk_id_to_pos
    ]
    expanded_hits = sort_hits(expanded_hits, meta)
    return expanded_hits, seed_n, neighbors_added, len(expanded_hits)
