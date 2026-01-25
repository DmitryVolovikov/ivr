from __future__ import annotations

import logging
import os
import time
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.document_processing import CLEANING_VERSION
from . import bm25, faiss_index, postprocess, rrf
from app.services.retrieval.index_store import (
    IndexData,
    clear_index_files,
    corpus_version,
    current_fingerprint,
    index_paths,
    load_meta,
    mark_dirty_file,
    save_meta,
)

BM25_TOP_K = 200
VECTOR_TOP_K = 200
RRF_C = 60

logger = logging.getLogger(__name__)

_index_cache: IndexData | None = None


def _safe_int_env(key: str, default: int) -> int:
    raw_value = os.getenv(key)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _debug_config(force: bool | None = None) -> tuple[bool, int, int]:
    if force is None:
        enabled = os.getenv("RAG_DEBUG") == "1"
    else:
        enabled = force
    if not enabled:
        return False, 0, 0
    top_n = _safe_int_env("RAG_DEBUG_TOP", 5)
    text_chars = _safe_int_env("RAG_DEBUG_TEXT_CHARS", 200)
    return True, max(0, top_n), max(0, text_chars)


def _short(text: str, n: int) -> str:
    if n <= 0:
        return ""
    cleaned_chars: list[str] = []
    for char in text:
        if char in {"\n", "\r", "\t"}:
            cleaned_chars.append(" ")
        elif not char.isprintable():
            cleaned_chars.append(" ")
        else:
            cleaned_chars.append(char)
    cleaned = "".join(cleaned_chars)
    collapsed = " ".join(cleaned.split())
    if len(collapsed) > n:
        return f"{collapsed[:n]}…"
    return collapsed


def _format_hits_block(
    title: str,
    hits: list[tuple[int, float]],
    meta: list[dict[str, int]],
    text_by_chunk_id: dict[int, str],
    *,
    top_n: int,
    text_chars: int,
) -> str:
    lines = [f"{title} (top {top_n})"]
    for rank, (idx, score) in enumerate(hits[:top_n], start=1):
        meta_item = meta[idx]
        chunk_id = meta_item.get("chunk_id", 0)
        preview = ""
        raw_text = text_by_chunk_id.get(chunk_id)
        if raw_text:
            preview = _short(raw_text, text_chars)
        preview_note = f' preview="{preview}"' if preview else " preview=unavailable"
        lines.append(
            " ".join(
                [
                    f"{rank:02d}.",
                    f"pos_idx={idx}",
                    f"score={score:.6f}",
                    f"chunk_id={chunk_id}",
                    f"doc_id={meta_item.get('doc_id', 0)}",
                    f"chunk_index={meta_item.get('chunk_index', 0)}",
                    preview_note,
                ]
            )
        )
    return "\n".join(lines)


def _fetch_chunk_texts(
    db: Session,
    chunk_ids: list[int],
) -> dict[int, str]:
    if not chunk_ids:
        return {}
    chunks = db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()
    return {chunk.id: chunk.text for chunk in chunks}


def _build_index(db: Session, model: faiss_index.SentenceTransformer | None) -> IndexData:
    paths = index_paths()
    chunks = (
        db.query(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.status == "published")
        .order_by(DocumentChunk.id.asc())
        .all()
    )
    if not chunks:
        if paths:
            clear_index_files(paths)
            paths["dirty"].unlink(missing_ok=True)
        return IndexData(
            backend="none",
            use_faiss=False,
            index=None,
            embeddings=None,
            meta=[],
            bm25=None,
            corpus_version=(0, 0),
        )

    texts = [chunk.text for chunk in chunks]
    meta = [
        {
            "doc_id": chunk.document_id,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
        }
        for chunk in chunks
    ]
    bm25_index = bm25.build_bm25(texts)
    model_name = faiss_index.effective_model_name()
    use_faiss, index, embeddings = faiss_index.build_faiss_index(
        texts,
        model,
        model_name=model_name,
        paths=paths,
    )
    fingerprint = current_fingerprint(
        model_name,
        embedding_dim=faiss_index.embedding_dim(model, embeddings),
        tokenizer_version=bm25.BM25_TOKENIZER_VERSION,
        cleaning_version=CLEANING_VERSION,
        embedding_prefix_mode=faiss_index.is_e5(model_name),
    )
    if paths:
        save_meta(paths, meta, fingerprint)
        paths["dirty"].unlink(missing_ok=True)
    return IndexData(
        backend=model_name if model is not None else "none",
        use_faiss=use_faiss and index is not None,
        index=index,
        embeddings=embeddings,
        meta=meta,
        bm25=bm25_index,
        corpus_version=corpus_version(meta),
    )


def _load_index(model: faiss_index.SentenceTransformer | None) -> IndexData | None:
    paths = index_paths()
    if not paths or paths["dirty"].exists():
        return None
    meta, fingerprint = load_meta(paths)
    embeddings = faiss_index.load_embeddings(paths)
    model_name = faiss_index.effective_model_name()
    current = current_fingerprint(
        model_name,
        embedding_dim=faiss_index.embedding_dim(model, embeddings),
        tokenizer_version=bm25.BM25_TOKENIZER_VERSION,
        cleaning_version=CLEANING_VERSION,
        embedding_prefix_mode=faiss_index.is_e5(model_name),
    )
    if fingerprint is None or fingerprint != current:
        paths["dirty"].touch(exist_ok=True)
        logger.warning("Index metadata fingerprint mismatch; marking index dirty.")
        return None
    if not meta:
        return IndexData(
            backend="none",
            use_faiss=False,
            index=None,
            embeddings=None,
            meta=[],
            bm25=None,
            corpus_version=(0, 0),
        )

    index = faiss_index.load_faiss_index(paths)
    if (
        model is not None
        and faiss_index.FAISS_AVAILABLE
        and faiss_index.faiss is not None
        and faiss_index.NUMPY_AVAILABLE
        and index is not None
    ):
        return IndexData(
            backend=model_name,
            use_faiss=True,
            index=index,
            embeddings=embeddings,
            meta=meta,
            bm25=None,
            corpus_version=corpus_version(meta),
        )
    return IndexData(
        backend=model_name if model is not None else "none",
        use_faiss=False,
        index=None,
        embeddings=embeddings,
        meta=meta,
        bm25=None,
        corpus_version=corpus_version(meta),
    )


def _validate_index_data(index_data: IndexData) -> None:
    try:
        meta_len = len(index_data.meta)
        if index_data.bm25 is not None:
            bm25_len = getattr(index_data.bm25, "corpus_size", meta_len)
            assert bm25_len == meta_len
        if index_data.embeddings is not None:
            assert index_data.embeddings.shape[0] == meta_len
        if index_data.use_faiss and index_data.index is not None:
            assert index_data.index.ntotal == meta_len
        if meta_len >= 2:
            first, second = 0, 1
            hits = [(first, 1.0), (second, 1.0)]
            sorted_hits = rrf.sort_hits(hits, index_data.meta)
            expected = sorted(
                [first, second],
                key=lambda idx: rrf.tie_break_key(index_data.meta[idx]),
            )
            assert [idx for idx, _ in sorted_hits][:2] == expected
    except AssertionError:
        logger.warning("Index self-check failed; consider rebuilding the index.")


def ensure_index(db: Session) -> IndexData:
    global _index_cache
    backend, model = faiss_index.get_embedding_backend()
    paths = index_paths()
    if (
        _index_cache
        and _index_cache.backend == backend
        and not (paths and paths["dirty"].exists())
    ):
        if _index_cache.bm25 is None:
            _index_cache = bm25.attach_bm25(db, _index_cache)
            _index_cache.corpus_version = corpus_version(_index_cache.meta)
        _validate_index_data(_index_cache)
        return _index_cache

    loaded = _load_index(model)
    if loaded is not None:
        loaded = bm25.attach_bm25(db, loaded)
        loaded.corpus_version = corpus_version(loaded.meta)
        _validate_index_data(loaded)
        _index_cache = loaded
        return loaded

    built = _build_index(db, model)
    _validate_index_data(built)
    _index_cache = built
    return built


def mark_index_dirty() -> None:
    global _index_cache
    _index_cache = None
    mark_dirty_file()


def _retriever_label(
    *,
    has_bm25: bool,
    has_vector: bool,
    use_rrf: bool,
    use_neighbors: bool,
) -> str:
    if has_bm25 and has_vector:
        label = "bm25_faiss_rrf" if use_rrf else "bm25_faiss"
    elif has_bm25:
        label = "bm25_only"
    elif has_vector:
        label = "faiss_only"
    else:
        label = "none"
    if not use_neighbors:
        return f"{label}_neighbors_off"
    return label


def retrieve_chunks(
    db: Session,
    query: str,
    limit: int,
    *,
    use_bm25: bool = True,
    use_faiss: bool = True,
    use_rrf: bool = True,
    use_neighbors: bool = True,
    neighbors_window: int = 2,
    seed_n: int = 10,
    bm25_top_k: int = BM25_TOP_K,
    vec_top_k: int = VECTOR_TOP_K,
    rrf_c: int = RRF_C,
    debug: bool | None = None,
) -> tuple[list[tuple[int, float]], str]:
    debug_enabled, debug_top, debug_text_chars = _debug_config(debug)
    index_data = ensure_index(db)

    has_bm25 = use_bm25 and index_data.bm25 is not None
    has_vector = use_faiss and index_data.use_faiss and index_data.index is not None
    retriever = _retriever_label(
        has_bm25=has_bm25,
        has_vector=has_vector,
        use_rrf=use_rrf,
        use_neighbors=use_neighbors,
    )
    if not index_data.meta:
        return [], retriever

    fingerprint: dict[str, Any] | None = None
    if debug_enabled:
        paths = index_paths()
        if paths:
            _, fingerprint = load_meta(paths)
        logger.debug(
            "RAG debug query=%r limit=%s backend=%s retriever=%s corpus_version=%s fingerprint=%s",
            query,
            limit,
            index_data.backend,
            retriever,
            index_data.corpus_version,
            fingerprint,
        )

    max_candidates = len(index_data.meta)
    candidates = min(max_candidates, max(80, limit * 10))
    bm25_hits: list[tuple[int, float]] = []
    vector_hits: list[tuple[int, float]] = []

    if debug_enabled:
        bm25_start = time.perf_counter()
    if has_bm25:
        bm25_hits = bm25.bm25_search(
            index_data,
            query,
            min(bm25_top_k, candidates),
            sort_hits=rrf.sort_hits,
        )
    if debug_enabled:
        bm25_time = time.perf_counter() - bm25_start
        vector_start = time.perf_counter()
    if has_vector:
        vector_hits = faiss_index.vector_search(
            index_data,
            query,
            min(vec_top_k, candidates),
            sort_hits=rrf.sort_hits,
        )
    if debug_enabled:
        vector_time = time.perf_counter() - vector_start

    if debug_enabled:
        rrf_start = time.perf_counter()
    if has_bm25 and has_vector and use_rrf:
        fused = rrf.rrf_fuse(
            bm25_hits,
            vector_hits,
            index_data.meta,
            candidates,
            rrf_c=rrf_c,
        )
    else:
        fused = bm25_hits or vector_hits
    fused = fused[: min(candidates, len(fused))]
    if debug_enabled:
        rrf_time = time.perf_counter() - rrf_start

    if use_neighbors and fused:
        if debug_enabled:
            neighbor_start = time.perf_counter()
        expanded, seed_n, neighbors_added, deduped_count = postprocess.expand_neighbors_with_lookup(
            fused,
            index_data.meta,
            seed_n=seed_n,
            neighbors_window=neighbors_window,
            neighbor_lookup=postprocess.neighbor_lookup(db, neighbors_window=neighbors_window),
        )
        if debug_enabled:
            neighbor_time = time.perf_counter() - neighbor_start
    else:
        expanded = fused
        neighbors_added = 0
        deduped_count = len(expanded)
        neighbor_time = 0.0

    if debug_enabled:
        bm25_indices = {idx for idx, _ in bm25_hits}
        vector_indices = {idx for idx, _ in vector_hits}
        final_hits = expanded[: min(limit, len(expanded))]
        final_indices = {idx for idx, _ in final_hits}
        logger.debug(
            "RAG debug timings bm25=%.4fs (%s hits) vector=%.4fs (%s hits) rrf=%.4fs (%s hits) "
            "neighbors=%.4fs (%s hits, added=%s, deduped=%s) intersections bm25∩vector=%s "
            "final∩bm25=%s",
            bm25_time,
            len(bm25_hits),
            vector_time,
            len(vector_hits),
            rrf_time,
            len(fused),
            neighbor_time,
            len(expanded),
            neighbors_added,
            deduped_count,
            len(bm25_indices & vector_indices),
            len(final_indices & bm25_indices),
        )
        logger.debug(
            "RAG debug candidate counts bm25=%s vector=%s fused=%s expanded=%s final=%s",
            len(bm25_hits),
            len(vector_hits),
            len(fused),
            len(expanded),
            len(final_hits),
        )
        if debug_top > 0:
            indices_to_preview: set[int] = set()
            for hit_list in (bm25_hits, vector_hits, fused, expanded, final_hits):
                indices_to_preview.update(idx for idx, _ in hit_list[:debug_top])
            text_by_chunk_id: dict[int, str] = {}
            if indices_to_preview:
                chunk_ids = [index_data.meta[idx]["chunk_id"] for idx in indices_to_preview]
                try:
                    text_by_chunk_id = _fetch_chunk_texts(db, chunk_ids)
                except SQLAlchemyError as exc:
                    logger.debug("RAG debug preview fetch failed.", exc_info=exc)
                    text_by_chunk_id = {}
            logger.debug(
                "%s",
                _format_hits_block(
                    "BM25 hits",
                    bm25_hits,
                    index_data.meta,
                    text_by_chunk_id,
                    top_n=debug_top,
                    text_chars=debug_text_chars,
                ),
            )
            logger.debug(
                "%s",
                _format_hits_block(
                    "Vector hits",
                    vector_hits,
                    index_data.meta,
                    text_by_chunk_id,
                    top_n=debug_top,
                    text_chars=debug_text_chars,
                ),
            )
            logger.debug(
                "%s",
                _format_hits_block(
                    "RRF fused hits",
                    fused,
                    index_data.meta,
                    text_by_chunk_id,
                    top_n=debug_top,
                    text_chars=debug_text_chars,
                ),
            )
            logger.debug(
                "%s",
                _format_hits_block(
                    "Post-processing (neighbors)",
                    expanded,
                    index_data.meta,
                    text_by_chunk_id,
                    top_n=debug_top,
                    text_chars=debug_text_chars,
                ),
            )
            logger.debug(
                "%s",
                _format_hits_block(
                    "Final hits",
                    final_hits,
                    index_data.meta,
                    text_by_chunk_id,
                    top_n=debug_top,
                    text_chars=debug_text_chars,
                ),
            )

    model_name = faiss_index.effective_model_name()
    logger.debug(
        "Retrieval candidates=%s seed_n=%s neighbors_added=%s deduped_count=%s backend=%s model=%s",
        candidates,
        seed_n,
        neighbors_added,
        deduped_count,
        retriever,
        model_name,
    )

    hits = []
    for idx, score in expanded[: min(limit, len(expanded))]:
        meta = index_data.meta[idx]
        hits.append((meta["chunk_id"], float(score)))
    return hits, retriever


def search_chunks_with_meta(
    db: Session,
    query: str,
    limit: int,
) -> tuple[list[tuple[int, float]], str]:
    return retrieve_chunks(db, query, limit)


def search_chunks(db: Session, query: str, limit: int) -> list[tuple[int, float]]:
    hits, _ = search_chunks_with_meta(db, query, limit)
    return hits
