from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.storage import ensure_storage_dirs

INDEX_FILENAME = "index.faiss"
META_FILENAME = "meta.json"
DIRTY_FILENAME = "dirty.flag"
EMBEDDINGS_FILENAME = "embeddings.npy"


@dataclass
class IndexData:
    backend: str
    use_faiss: bool
    index: Any | None
    embeddings: Any | None
    meta: list[dict[str, int]]
    bm25: Any | None
    corpus_version: tuple[int, int]


def index_paths() -> dict[str, Path] | None:
    base = Path(settings.indexes_path)
    if not base.exists():
        return None
    ensure_storage_dirs()
    return {
        "index": base / INDEX_FILENAME,
        "meta": base / META_FILENAME,
        "dirty": base / DIRTY_FILENAME,
        "embeddings": base / EMBEDDINGS_FILENAME,
    }


def mark_dirty_file() -> None:
    paths = index_paths()
    if paths:
        paths["dirty"].touch(exist_ok=True)


def clear_index_files(paths: dict[str, Path]) -> None:
    for key in ("index", "meta", "embeddings"):
        try:
            paths[key].unlink(missing_ok=True)
        except OSError:
            pass


def save_meta(
    paths: dict[str, Path],
    meta: list[dict[str, int]],
    fingerprint: dict[str, str | int | bool],
) -> None:
    payload = {"chunks": meta, "fingerprint": fingerprint}
    paths["meta"].write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_meta(
    paths: dict[str, Path],
) -> tuple[list[dict[str, int]], dict[str, Any] | None]:
    if not paths["meta"].exists():
        return [], None
    data = json.loads(paths["meta"].read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        meta = data.get("chunks", [])
        if not isinstance(meta, list):
            meta = []
        fingerprint = data.get("fingerprint")
        return meta, fingerprint if isinstance(fingerprint, dict) else None
    return [], None


def current_fingerprint(
    model_name: str,
    *,
    embedding_dim: str | int,
    tokenizer_version: str,
    cleaning_version: str,
    embedding_prefix_mode: bool,
) -> dict[str, str | int | bool]:
    return {
        "embedding_model_name": model_name,
        "embedding_prefix_mode": embedding_prefix_mode,
        "embedding_dim": embedding_dim,
        "tokenizer_version": tokenizer_version,
        "CLEANING_VERSION": cleaning_version,
    }


def corpus_version(meta: list[dict[str, int]]) -> tuple[int, int]:
    max_chunk_id = max((item.get("chunk_id", 0) for item in meta), default=0)
    return (len(meta), max_chunk_id)
