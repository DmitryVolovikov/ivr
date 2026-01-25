from __future__ import annotations

import app.services.retrieval.rrf as rrf


def run() -> int:
    meta = [
        {"doc_id": 1, "chunk_index": 0, "chunk_id": 10},
        {"doc_id": 1, "chunk_index": 1, "chunk_id": 11},
        {"doc_id": 2, "chunk_index": 0, "chunk_id": 20},
    ]
    bm25_hits = [(0, 1.0), (2, 0.9)]
    vector_hits = [(1, 0.8), (2, 0.7)]
    fused = rrf.rrf_fuse(bm25_hits, vector_hits, meta, limit=3, rrf_c=60)
    sorted_hits = rrf.sort_hits([(1, 1.0), (0, 1.0)], meta)
    if not fused or [idx for idx, _ in sorted_hits][:2] != [0, 1]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
