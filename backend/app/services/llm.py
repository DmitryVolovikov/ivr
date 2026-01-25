from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Sequence

import requests
from requests import exceptions as request_exceptions

from app.core.config import settings

logger = logging.getLogger(__name__)

NO_SOURCES_ANSWER = "Не нашёл в документах. Уточните, пожалуйста, вопрос."
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class LLMResult:
    answer: str
    provider: str
    model: str
    error: str | None = None


class SourceItem:
    def __init__(
        self,
        source_no: int,
        snippet: str,
        score: float | None = None,
        *,
        title: str | None = None,
        chunk_id: int | None = None,
        llm_excerpt: str | None = None,
    ) -> None:
        self.source_no = source_no
        self.snippet = snippet
        self.score = score
        self.title = title
        self.chunk_id = chunk_id
        self.llm_excerpt = llm_excerpt


def _safe_int_env(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def top_sources_for_prompt(sources: Sequence[SourceItem], k: int = 5) -> list[SourceItem]:
    if not sources:
        return []
    return list(sources[:k])


def trim_sources_by_char_budget(
    sources: Sequence[SourceItem],
    max_chars: int,
) -> list[SourceItem]:
    if max_chars <= 0:
        return []
    total = 0
    kept: list[SourceItem] = []
    for source in sources:
        excerpt = (source.llm_excerpt or source.snippet or "").strip()
        if not excerpt:
            continue
        length = len(excerpt)
        if total + length > max_chars:
            break
        kept.append(source)
        total += length
    return kept

def _build_prompt(question: str, sources: Sequence[SourceItem]) -> str:
    sources_block = "\n\n".join(
        f"[S{source.source_no}] {(source.llm_excerpt or source.snippet).rstrip()}"
        for source in sources
        if (source.llm_excerpt or source.snippet or "").strip()
    )
    if not sources_block.strip():
        sources_block = "[no sources]"

    return (
        "You are LyceumDocBot, a QA assistant for official Lyceum documents.\n"
        "Answer the user's question using ONLY the Evidence.\n"
        "\n"
        "HARD RULES (must follow):\n"
        "1) Use ONLY the Evidence. Do NOT use any outside knowledge (including arithmetic, common facts, assumptions).\n"
        "2) If the Evidence does not contain the answer, output EXACTLY this sentence and nothing else:\n"
        "   \"В документах нету ответа на данный вопрос.\"\n"
        "3) Every sentence in your answer MUST end with at least one citation like [S1].\n"
        "   If you cannot cite a sentence, you MUST output the exact refusal sentence from rule (2).\n"
        "4) If sources conflict, state that they conflict and give both versions, each with citations.\n"
        "5) Write in Russian. Keep 1–5 sentences.\n"
        "\n"
        f"Evidence:\n{sources_block}\n"
        "\n"
        f"Question:\n{question}\n"
        "\n"
        "Answer:"
    )


def _format_source_title(source: SourceItem) -> str:
    title = (source.title or f"Документ {source.source_no}").strip()
    if source.chunk_id is not None:
        return f"{title} (фрагмент {source.chunk_id})"
    return title


def build_failure_answer(sources: Sequence[SourceItem]) -> str:
    lines = [
        f"- {_format_source_title(source)} [S{source.source_no}]"
        for source in sources
    ]
    sources_block = "\n".join(lines) if lines else "- [S1]"
    return (
        "Извините, не удалось сформировать ответ по документам.\n"
        "Источники:\n"
        f"{sources_block}"
    )


def _ollama_payload(prompt: str, *, model: str) -> dict[str, object]:
    stop_sequences = [s.strip() for s in settings.ollama_stop.split(",") if s.strip()]
    payload: dict[str, object] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": settings.ollama_temperature,
            "top_p": settings.ollama_top_p,
            "top_k": settings.ollama_top_k,
            "repeat_penalty": settings.ollama_repeat_penalty,
            # Default to a modest generation limit for slower CPU Ollama unless overridden via env.
            "num_predict": settings.ollama_num_predict,
        },
    }
    if stop_sequences:
        payload["options"]["stop"] = stop_sequences
    seed = _safe_int_env(settings.ollama_seed, -1)
    if seed >= 0:
        payload["options"]["seed"] = seed
    return payload


def _is_missing_model_error(exc: request_exceptions.HTTPError) -> bool:
    response = exc.response
    if response is None:
        return False
    if response.status_code in {404, 400}:
        try:
            data = response.json()
        except ValueError:
            data = {}
        message = (data.get("error") or "").lower()
        if "model" in message and ("not found" in message or "missing" in message):
            return True
        if response.status_code == 404:
            return True
    return False


def _ollama_request(prompt: str, *, model: str) -> str:
    max_attempts = 2
    backoff_base = 0.4
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = requests.post(
                f"{settings.ollama_base_url}/api/generate",
                json=_ollama_payload(prompt, model=model),
                # CPU Ollama can take minutes; keep the read timeout high to avoid proxy resets.
                timeout=(10, 600),
            )
            response.raise_for_status()
            data = response.json()
            return (data.get("response") or "").strip()
        except request_exceptions.Timeout as exc:
            last_exc = exc
            retryable = True
        except request_exceptions.HTTPError as exc:
            last_exc = exc
            status_code = exc.response.status_code if exc.response is not None else None
            retryable = status_code in RETRYABLE_STATUS_CODES
        except ValueError as exc:
            last_exc = exc
            retryable = False
        except request_exceptions.RequestException as exc:
            last_exc = exc
            retryable = False

        if retryable and attempt < max_attempts - 1:
            delay = backoff_base * (2**attempt)
            logger.warning(
                "Ollama request failed (%s), retrying in %.2fs (attempt %s/%s).",
                type(last_exc).__name__,
                delay,
                attempt + 1,
                max_attempts,
            )
            time.sleep(delay)
            continue
        if last_exc is not None:
            raise last_exc
    raise RuntimeError("Ollama request failed unexpectedly.")


def generate_answer_with_meta(
    question: str,
    sources: Sequence[SourceItem],
) -> LLMResult:
    if not sources:
        return LLMResult(answer=NO_SOURCES_ANSWER, provider="stub", model="stub")
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        prompt_sources = top_sources_for_prompt(sources, k=settings.llm_sources_k)
        prompt_sources = trim_sources_by_char_budget(prompt_sources, settings.llm_sources_char_limit)
        prompt = _build_prompt(question, prompt_sources)
        try:
            answer = _ollama_request(prompt, model=settings.ollama_model)
            return LLMResult(
                answer=answer,
                provider="ollama",
                model=settings.ollama_model,
            )
        except request_exceptions.HTTPError as exc:
            if _is_missing_model_error(exc) and settings.ollama_fallback_model:
                fallback_model = settings.ollama_fallback_model
                logger.warning(
                    "Ollama model %s not found; falling back to %s.",
                    settings.ollama_model,
                    fallback_model,
                )
                try:
                    answer = _ollama_request(prompt, model=fallback_model)
                    return LLMResult(
                        answer=answer,
                        provider="ollama",
                        model=fallback_model,
                    )
                except (request_exceptions.RequestException, ValueError) as fallback_exc:
                    logger.warning(
                        "Ollama fallback request failed; falling back to sources.",
                        exc_info=fallback_exc,
                    )
                    error = f"{fallback_exc.__class__.__name__}"
                    answer = build_failure_answer(sources)
                    return LLMResult(
                        answer=answer,
                        provider="stub",
                        model="stub",
                        error=error,
                    )
            logger.warning("Ollama request failed; falling back to sources.", exc_info=exc)
            error = f"{exc.__class__.__name__}"
            answer = build_failure_answer(sources)
            return LLMResult(answer=answer, provider="stub", model="stub", error=error)
        except (request_exceptions.RequestException, ValueError) as exc:
            logger.warning("Ollama request failed; falling back to sources.", exc_info=exc)
            error = f"{exc.__class__.__name__}"
            answer = build_failure_answer(sources)
            return LLMResult(answer=answer, provider="stub", model="stub", error=error)
    answer = build_failure_answer(sources)
    return LLMResult(answer=answer, provider="stub", model="stub")


def generate_answer(question: str, sources: Sequence[SourceItem]) -> str:
    return generate_answer_with_meta(question, sources).answer
