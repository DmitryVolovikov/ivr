import re
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from app.services.text_utils import clean_text_v3

SENTENCE_BOUNDARY_RE = re.compile(r".+?(?:[.!?…]+(?=\s|$)|$)\s*", re.DOTALL)
CLEANING_VERSION = "v3-join-hyphen-newlines-clean-text"


def extract_text_from_file(path: Path, mime_type: str) -> str:
    suffix = path.suffix.lower()
    if mime_type == "application/pdf" or suffix == ".pdf":
        reader = PdfReader(str(path))
        pages_text = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages_text)
    if suffix in {".txt", ".md"} or mime_type.startswith("text/"):
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError("Unsupported file type")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\u00ad", "")
    cleaned = re.sub(r"([А-Яа-яЁё])-\n([А-Яа-яЁё])", r"\1\2", cleaned)
    cleaned = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", cleaned)
    return clean_text_v3(cleaned, keep_newlines=True)


def _split_with_separator(text, separator):
    parts = text.split(separator)
    if len(parts) == 1:
        return [text]
    results: list[str] = []
    for idx, part in enumerate(parts):
        if idx < len(parts) - 1:
            results.append(part + separator)
        elif part:
            results.append(part)
    return [segment for segment in results if segment]


def _split_by_sentence(text):
    matches = [match.group(0) for match in SENTENCE_BOUNDARY_RE.finditer(text) if match.group(0).strip()]
    return matches or [text]


def _hard_split(text, chunk_size):
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break
        cutoff = remaining.rfind(" ", 0, chunk_size + 1)
        if cutoff == -1:
            cutoff = remaining.find(" ", chunk_size)
        if cutoff == -1:
            cutoff = min(chunk_size, len(remaining))
        chunk = remaining[:cutoff].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cutoff:].lstrip()
    return chunks


def _split_recursive(text, chunk_size, separators):
    if len(text) <= chunk_size:
        return [text]
    if not separators:
        return _hard_split(text, chunk_size)
    separator = separators[0]
    if separator == "SENTENCE":
        parts = _split_by_sentence(text)
    else:
        parts = _split_with_separator(text, separator)
    results: list[str] = []
    for part in parts:
        if len(part) <= chunk_size:
            results.append(part)
        else:
            results.extend(_split_recursive(part, chunk_size, separators[1:]))
    return results


def _overlap_tail(text, max_length):
    if max_length <= 0 or not text:
        return ""
    tail = text[-max_length:]
    match = re.search(r"\s", tail)
    if match:
        tail = tail[match.start() + 1 :]
    return tail.strip()


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 150) -> Iterable[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if not text or not text.strip():
        return []

    separators = ["\n\n", "\n", "SENTENCE", " "]
    units = _split_recursive(text, chunk_size, separators)
    units = [unit for unit in units if unit.strip()]
    if not units:
        return []

    chunks: list[str] = []
    current = ""
    max_overlap = min(overlap, chunk_size - 1)
    for unit in units:
        candidate = f"{current}{unit}" if current else unit
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
        overlap_text = _overlap_tail(current, max_overlap)
        if overlap_text:
            separator = ""
            if not overlap_text[-1].isspace() and unit and not unit[0].isspace():
                separator = " "
            candidate = f"{overlap_text}{separator}{unit}".strip()
            if len(candidate) <= chunk_size:
                current = candidate
                continue
        current = unit

    if current.strip():
        chunks.append(current.strip())
    return chunks
