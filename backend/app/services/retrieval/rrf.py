from __future__ import annotations

from typing import Iterable


def tie_break_key(meta: dict[str, int]) -> tuple[int, int, int]:
    return (
        meta.get("doc_id", 0),
        meta.get("chunk_index", 0),
        meta.get("chunk_id", 0),
    )


def sort_hits(
    hits: Iterable[tuple[int, float]],
    meta: list[dict[str, int]],
) -> list[tuple[int, float]]:
    return sorted(hits, key=lambda item: (-item[1], tie_break_key(meta[item[0]])))


def rrf_fuse(
    bm25_hits: list[tuple[int, float]],
    vector_hits: list[tuple[int, float]],
    meta: list[dict[str, int]],
    limit: int,
    *,
    rrf_c: int = 60,
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for rank, (idx, _) in enumerate(bm25_hits):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_c + rank + 1)
    for rank, (idx, _) in enumerate(vector_hits):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (rrf_c + rank + 1)
    combined = [(idx, score) for idx, score in scores.items()]
    combined_sorted = sorted(
        combined, key=lambda item: (-item[1], tie_break_key(meta[item[0]]))
    )
    return combined_sorted[: min(limit, len(combined_sorted))]
