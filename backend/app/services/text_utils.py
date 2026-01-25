import html
import re
import unicodedata

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\u2060\uFEFF]")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")
PUNCTUATION_SPACE_RE = re.compile(r"\s+([,.;:!?%])")
CLOSING_PUNCT_SPACE_RE = re.compile(r"\s+([)\]}])")

TYPOGRAPHY_TRANSLATION = str.maketrans(
    {
        "“": "\"",
        "”": "\"",
        "„": "\"",
        "«": "\"",
        "»": "\"",
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "—": "-",
        "–": "-",
        "‑": "-",
        "‒": "-",
    }
)


def _normalize_search_text(text):
    return text.lower().replace("ё", "е").replace("\u00ad", "")


def _normalize_typography(text):
    normalized = text.translate(TYPOGRAPHY_TRANSLATION)
    return normalized.replace("…", "...")


def _remove_whitespace_before_punct(text):
    text = PUNCTUATION_SPACE_RE.sub(r"\1", text)
    return CLOSING_PUNCT_SPACE_RE.sub(r"\1", text)


def clean_text(
    text: str,
    *,
    keep_newlines: bool = False,
    remove_urls_emails: bool = False,
) -> str:
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = ZERO_WIDTH_RE.sub("", cleaned)
    cleaned = CONTROL_CHARS_RE.sub("", cleaned)
    if remove_urls_emails:
        cleaned = URL_RE.sub("", cleaned)
        cleaned = EMAIL_RE.sub("", cleaned)
    if keep_newlines:
        lines = cleaned.splitlines()
        normalized_lines = []
        previous_blank = False
        for line in lines:
            collapsed = re.sub(r"[ \t]+", " ", line).strip()
            if not collapsed:
                if not previous_blank:
                    normalized_lines.append("")
                previous_blank = True
                continue
            normalized_lines.append(collapsed)
            previous_blank = False
        return "\n".join(normalized_lines).strip()
    return re.sub(r"\s+", " ", cleaned).strip()


def clean_text_v3(
    text: str,
    *,
    keep_newlines: bool = False,
    remove_urls_emails: bool = False,
) -> str:
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = _normalize_typography(cleaned)
    cleaned = ZERO_WIDTH_RE.sub("", cleaned)
    cleaned = CONTROL_CHARS_RE.sub("", cleaned)
    if remove_urls_emails:
        cleaned = URL_RE.sub("", cleaned)
        cleaned = EMAIL_RE.sub("", cleaned)
    cleaned = _remove_whitespace_before_punct(cleaned)
    if keep_newlines:
        lines = cleaned.split("\n")
        normalized_lines: list[str] = []
        blank_streak = 0
        for line in lines:
            line = re.sub(r"[ ]{2,}", " ", line)
            line = line.strip(" ")
            if not line.strip():
                blank_streak += 1
                if blank_streak <= 2:
                    normalized_lines.append("")
                continue
            blank_streak = 0
            normalized_lines.append(line)
        return "\n".join(normalized_lines).strip()
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = _remove_whitespace_before_punct(cleaned)
    return cleaned.strip()


def make_snippet(text: str, query: str | None = None, max_length: int = 200) -> str:
    cleaned = " ".join(text.split()).replace("\u00ad", "")
    if not cleaned:
        return ""
    if query:
        lower_text = _normalize_search_text(cleaned)
        lower_query = _normalize_search_text(query)
        idx = lower_text.find(lower_query)
        if idx != -1:
            start = max(0, idx - max_length // 4)
            end = min(len(cleaned), start + max_length)
            snippet = cleaned[start:end]
            return snippet if start == 0 else f"...{snippet}"
        raw_tokens = TOKEN_RE.findall(query)
        normalized_tokens = [
            _normalize_search_text(token)
            for token in raw_tokens
            if 3 <= len(token) <= 30
        ]
        if normalized_tokens:
            alpha_tokens = [token for token in normalized_tokens if token.isalpha()]
            tokens = alpha_tokens or normalized_tokens
            for token in sorted(tokens, key=len, reverse=True):
                idx = lower_text.find(token)
                if idx != -1:
                    start = max(0, idx - max_length // 4)
                    end = min(len(cleaned), start + max_length)
                    snippet = cleaned[start:end]
                    return snippet if start == 0 else f"...{snippet}"
    return cleaned[:max_length]


def make_llm_excerpt(
    text: str,
    query: str | None = None,
    max_length: int = 1200,
) -> str:
    cleaned = clean_text_v3(text, keep_newlines=True)
    if not cleaned:
        return ""

    def build_window(start, end):
        if len(cleaned) <= max_length:
            return cleaned
        span_center = max(0, (start + end) // 2)
        half = max_length // 2
        window_start = max(0, span_center - half)
        window_end = window_start + max_length
        if window_end > len(cleaned):
            window_end = len(cleaned)
            window_start = max(0, window_end - max_length)
        excerpt = cleaned[window_start:window_end]
        if window_start > 0:
            excerpt = f"...{excerpt}"
        if window_end < len(cleaned):
            excerpt = f"{excerpt}..."
        return excerpt

    if query:
        normalized_text = _normalize_search_text(cleaned)
        normalized_query = _normalize_search_text(query)
        if normalized_query:
            idx = normalized_text.find(normalized_query)
            if idx != -1:
                return build_window(idx, idx + len(normalized_query))
        raw_tokens = TOKEN_RE.findall(query)
        normalized_tokens = [
            _normalize_search_text(token)
            for token in raw_tokens
            if 3 <= len(token) <= 30
        ]
        if normalized_tokens:
            alpha_tokens = [token for token in normalized_tokens if token.isalpha()]
            tokens = alpha_tokens or normalized_tokens
            for token in sorted(tokens, key=len, reverse=True):
                idx = normalized_text.find(token)
                if idx != -1:
                    return build_window(idx, idx + len(token))

    return build_window(0, min(len(cleaned), max_length))
