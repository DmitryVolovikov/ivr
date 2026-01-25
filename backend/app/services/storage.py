from pathlib import Path

from app.core.config import settings


def ensure_storage_dirs() -> None:
    Path(settings.docs_path).mkdir(parents=True, exist_ok=True)
    Path(settings.indexes_path).mkdir(parents=True, exist_ok=True)
