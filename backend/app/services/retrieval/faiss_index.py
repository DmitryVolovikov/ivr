from __future__ import annotations

import importlib.util
import logging
import os
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.retrieval.index_store import IndexData

SentenceTransformer = None
SENTENCE_TRANSFORMERS_AVAILABLE = False
if importlib.util.find_spec("sentence_transformers") is not None:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True

np = None
NUMPY_AVAILABLE = False
if importlib.util.find_spec("numpy") is not None:
    import numpy as np

    NUMPY_AVAILABLE = True

faiss = None
FAISS_AVAILABLE = False
if importlib.util.find_spec("faiss") is not None:
    import faiss  # type: ignore

    FAISS_AVAILABLE = True

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_model_failed = False
_model_name: str | None = None


def effective_model_name() -> str:
    return os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-base")


def is_e5(model_name: str) -> bool:
    return "e5" in model_name.lower()


def embedding_dim(
    model: SentenceTransformer | None,
    embeddings: Any | None,
) -> str | int:
    if embeddings is not None:
        try:
            return int(embeddings.shape[1])
        except (AttributeError, TypeError, ValueError):
            pass
    if model is not None:
        try:
            return model.get_sentence_embedding_dimension()
        except (AttributeError, RuntimeError, ValueError):
            return "unknown"
    return "none"


def get_model() -> SentenceTransformer | None:
    global _model
    global _model_failed
    global _model_name
    model_name = effective_model_name()
    if _model is not None and _model_name == model_name:
        return _model
    if _model is None or _model_name != model_name:
        if _model_failed or not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None
        try:
            _model = SentenceTransformer(model_name, device="cpu")
            _model_name = model_name
        except (OSError, RuntimeError, ValueError) as exc:
            _model_failed = True
            _model = None
            _model_name = None
            logger.warning("SentenceTransformer unavailable.", exc_info=exc)
    return _model


def get_embedding_backend() -> tuple[str, SentenceTransformer | None]:
    model = get_model()
    model_name = effective_model_name()
    if model is None:
        return "none", None
    return model_name, model


def embed_texts(
    texts: list[str],
    model: SentenceTransformer,
    *,
    is_query: bool,
    model_name: str,
) -> Any:
    if is_e5(model_name):
        prefix = "query: " if is_query else "passage: "
        texts = [f"{prefix}{text}" for text in texts]
    return model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    ).astype("float32")


def build_faiss_index(
    texts: list[str],
    model: SentenceTransformer | None,
    *,
    model_name: str,
    paths: dict[str, Any] | None,
) -> tuple[bool, Any | None, Any | None]:
    use_faiss = bool(
        model is not None and FAISS_AVAILABLE and faiss is not None and NUMPY_AVAILABLE
    )
    if not use_faiss or model is None:
        return False, None, None
    embeddings = embed_texts(texts, model, is_query=False, model_name=model_name)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    if paths:
        faiss.write_index(index, str(paths["index"]))
        if NUMPY_AVAILABLE:
            np.save(paths["embeddings"], embeddings)
    return True, index, embeddings


def load_embeddings(paths: dict[str, Any]) -> Any | None:
    if not NUMPY_AVAILABLE:
        return None
    if not paths["embeddings"].exists():
        return None
    try:
        return np.load(paths["embeddings"])
    except (OSError, ValueError) as exc:
        logger.warning("Failed to load embeddings.npy.", exc_info=exc)
        return None


def load_faiss_index(paths: dict[str, Any]) -> Any | None:
    if not (FAISS_AVAILABLE and faiss is not None):
        return None
    if not paths["index"].exists():
        return None
    return faiss.read_index(str(paths["index"]))


def vector_search(
    index_data: IndexData,
    query: str,
    limit: int,
    *,
    sort_hits: Callable[[list[tuple[int, float]], list[dict[str, int]]], list[tuple[int, float]]],
) -> list[tuple[int, float]]:
    if not index_data.meta or not index_data.use_faiss or index_data.index is None:
        return []
    if limit <= 0:
        return []
    model = get_model()
    if model is None or not NUMPY_AVAILABLE:
        return []
    model_name = effective_model_name()
    query_embedding = embed_texts(
        [query],
        model,
        is_query=True,
        model_name=model_name,
    )[0]
    query_vector = np.expand_dims(query_embedding, axis=0)
    scores, indices = index_data.index.search(
        query_vector, min(limit, len(index_data.meta))
    )
    hits = []
    for idx, score in zip(indices[0], scores[0], strict=False):
        if idx == -1:
            continue
        hits.append((int(idx), float(score)))
    return sort_hits(hits, index_data.meta)
