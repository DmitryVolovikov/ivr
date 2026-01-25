from __future__ import annotations

import importlib.util
import re
from typing import Any, Callable, TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk

if TYPE_CHECKING:
    from app.services.retrieval.index_store import IndexData

BM25Okapi = None
BM25_AVAILABLE = False
if importlib.util.find_spec("rank_bm25") is not None:
    from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

    BM25_AVAILABLE = True

np = None
NUMPY_AVAILABLE = False
if importlib.util.find_spec("numpy") is not None:
    import numpy as np

    NUMPY_AVAILABLE = True

_NLP = None
if importlib.util.find_spec("spacy") is not None:
    try:
        import spacy  # type: ignore

        _NLP = spacy.load("ru_core_news_sm")
    except (OSError, RuntimeError, ValueError):
        _NLP = None

TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")
CYRILLIC_RE = re.compile(r"^[а-я]+$")
BM25_TOKENIZER_VERSION = "v2-yoe-soft-hyphen-char4gram-qfull-doccapped12"


def _normalize_token_text(text: str) -> str:
    return text.lower().replace("ё", "е").replace("\u00ad", "")


def _char_ngrams(token: str, n: int = 4, cap: int | None = None) -> list[str]:
    if len(token) < n:
        return []
    grams = [token[idx : idx + n] for idx in range(len(token) - n + 1)]
    if cap is not None:
        return grams[:cap]
    return grams


def tokenize_with_heading(
    text: str,
    heading: str | None = None,
    path: str | None = None,
    *,
    for_query: bool = False,
) -> list[str]:
    raw_tokens: list[str]
    if _NLP is not None:
        raw_tokens = [
            (token.lemma_ or token.text) for token in _NLP(text) if token.text.strip()
        ]
    else:
        raw_tokens = TOKEN_RE.findall(text)
    base_tokens: list[str] = []
    for token in raw_tokens:
        normalized = _normalize_token_text(token)
        if len(normalized) < 2:
            continue
        if normalized.isdigit():
            continue
        base_tokens.append(normalized)
    heading_tokens: list[str] = []
    path_tokens: list[str] = []
    if heading:
        heading_tokens = tokenize_with_heading(heading, for_query=for_query)
    if path:
        path_tokens = tokenize_with_heading(path, for_query=for_query)
    tokens = base_tokens + heading_tokens * 2 + path_tokens
    ngrams: list[str] = []
    for token in base_tokens:
        if for_query:
            ngrams.extend(_char_ngrams(token))
        elif len(token) >= 6 and CYRILLIC_RE.match(token):
            ngrams.extend(_char_ngrams(token, cap=12))
    return tokens + ngrams


def tokenize(text: str, *, for_query: bool = False) -> list[str]:
    return tokenize_with_heading(text, for_query=for_query)


def build_bm25(texts: list[str]) -> Any | None:
    if not texts or not BM25_AVAILABLE or BM25Okapi is None:
        return None
    tokenized_corpus = [tokenize(text) for text in texts]
    return BM25Okapi(tokenized_corpus)


def attach_bm25(db: Session, index_data: IndexData) -> IndexData:
    if not index_data.meta or not BM25_AVAILABLE:
        index_data.bm25 = None
        return index_data
    chunk_ids = [meta_item["chunk_id"] for meta_item in index_data.meta]
    chunks = (
        db.query(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.status == "published")
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )
    chunk_map = {chunk.id: chunk for chunk in chunks}
    texts: list[str] = []
    ordered_meta: list[dict[str, int]] = []
    for meta_item in index_data.meta:
        chunk = chunk_map.get(meta_item["chunk_id"])
        if chunk is None:
            continue
        texts.append(chunk.text)
        ordered_meta.append(
            {
                "doc_id": chunk.document_id,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
            }
        )
    index_data.meta = ordered_meta
    index_data.bm25 = build_bm25(texts)
    return index_data


def bm25_search(
    index_data: IndexData,
    query: str,
    limit: int,
    *,
    sort_hits: Callable[[list[tuple[int, float]], list[dict[str, int]]], list[tuple[int, float]]],
) -> list[tuple[int, float]]:
    if index_data.bm25 is None:
        return []
    tokens = tokenize(query, for_query=True)
    if not tokens:
        return []
    scores = index_data.bm25.get_scores(tokens)
    if NUMPY_AVAILABLE and isinstance(scores, np.ndarray):
        top_k = min(limit, len(scores))
        if top_k <= 0:
            return []
        top_indices = np.argpartition(-scores, top_k - 1)[:top_k]
        hits = [
            (int(idx), float(scores[int(idx)]))
            for idx in top_indices
            if scores[int(idx)] > 0
        ]
    else:
        hits = [(idx, float(score)) for idx, score in enumerate(scores) if score > 0]
    return sort_hits(hits, index_data.meta)[: min(limit, len(hits))]
