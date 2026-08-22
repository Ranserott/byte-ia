"""Language detection and configuration helpers for the speech subsystem.

This module centralises the logic for:

* Choosing a default STT language (``es``, ``en``, ``pt``, ...) — read from
  the user's ``~/.openjarvis/config.yaml`` and fall back to ``"es"`` for
  Spanish-first users (matching the rest of the project defaults).
* Auto-detecting the spoken language from the user's text. The detector
  is intentionally tiny (no external services, no heavy ML deps): it
  looks for diacritics, common stop-words, and accent markers typical
  of Spanish/English/Portuguese.
* Mapping STT language codes to TTS voice ids for the bundled backends
  (Kokoro prefixes ``ef_*`` / ``em_*`` for Spanish, etc., and macOS ``say``
  exposes voices like ``"Monica"`` / ``"Juan"``).

The module is dependency-free so it can be imported from anywhere in the
speech subsystem (and tests) without dragging in optional deps.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


# Default language for users who never configured one. Spanish-first
# matches the project's user-facing language.
DEFAULT_LANGUAGE = "es"

# BCP-47 codes we currently recognise in the bundled STT/TTS backends.
SUPPORTED_LANGUAGES = ("es", "en", "pt", "fr", "it", "de", "zh", "ja")


@dataclass(slots=True)
class LanguageDetection:
    """Result of :func:`detect_language_from_text`."""

    code: str  # BCP-47 code, e.g. "es"
    confidence: float  # 0.0 – 1.0 heuristic confidence
    matched_tokens: int  # how many stop-word / diacritic matches we found


# ---------------------------------------------------------------------------
# Heuristic language detection
# ---------------------------------------------------------------------------

# Small, high-precision stop-word lists. Bigger lists would help but slow
# detection down on every utterance — these cover the vast majority of
# Spanish/English/Portuguese utterances in 5-10 words.
_ES_STOPWORDS = frozenset(
    {
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "y", "o", "pero", "porque", "como", "qué", "que", "cuál",
        "cómo", "dónde", "cuando", "si", "no", "sí", "ya",
        "yo", "tú", "él", "ella", "nosotros", "vosotros", "ellos",
        "mi", "tu", "su", "nuestro", "vuestro",
        "este", "esta", "estos", "estas", "ese", "esa",
        "para", "por", "con", "sin", "sobre", "entre",
        "hola", "gracias", "porfa", "por favor", "buenas",
        "hoy", "mañana", "ayer", "ahora",
    }
)
_EN_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "because", "as", "what", "which",
        "how", "where", "when", "if", "no", "yes",
        "i", "you", "he", "she", "we", "they",
        "my", "your", "his", "her", "our", "their",
        "this", "that", "these", "those", "for", "with", "without",
        "hello", "thanks", "please", "today", "tomorrow", "yesterday", "now",
    }
)
_PT_STOPWORDS = frozenset(
    {
        "o", "a", "os", "as", "um", "uma", "uns", "umas",
        "e", "ou", "mas", "porque", "como", "que", "qual",
        "eu", "tu", "ele", "ela", "nos", "vos", "eles",
        "meu", "teu", "seu", "nosso",
        "este", "esta", "estes", "estas", "esse", "essa",
        "para", "por", "com", "sem", "sobre", "entre",
        "olá", "obrigado", "obrigada", "por favor", "hoje", "amanhã",
    }
)

# Diacritics that are extremely common in Spanish (and Portuguese) but
# basically absent from English. One match is a very strong signal.
_ES_PT_DIACRITICS = "ñáéíóúü¿¡ãõâêîôûà"

# Map STT code -> language metadata used by TTS voice selection.
_LANGUAGE_META = {
    "es": {"name": "Spanish", "tts_prefix": "e", "macos_voices": ("Monica", "Juan", "Paulina")},
    "en": {"name": "English", "tts_prefix": "a", "macos_voices": ("Samantha", "Daniel", "Karen", "Alex")},
    "pt": {"name": "Portuguese", "tts_prefix": "p", "macos_voices": ("Luciana", "Joana")},
    "fr": {"name": "French", "tts_prefix": "f", "macos_voices": ("Amelie", "Thomas")},
    "it": {"name": "Italian", "tts_prefix": "i", "macos_voices": ("Alice", "Luca")},
    "de": {"name": "German", "tts_prefix": None, "macos_voices": ("Anna", "Markus")},
    "zh": {"name": "Chinese", "tts_prefix": "z", "macos_voices": ("Tingting", "Sin-ji")},
    "ja": {"name": "Japanese", "tts_prefix": "j", "macos_voices": ("Kyoko", "Otoya")},
}

_TOKEN_RE = re.compile(r"[\w¿¡]+", re.UNICODE)


def _tokens(text: str) -> List[str]:
    """Lowercase tokenisation that keeps Spanish inverted punctuation."""
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def detect_language_from_text(text: str) -> LanguageDetection:
    """Guess the language of *text* using cheap heuristics.

    The function never raises — it falls back to the configured default
    language on empty input or inconclusive evidence. The detector is
    intentionally dependency-free so it can run inside any backend that
    has access to the transcribed text.
    """
    if not text or not text.strip():
        return LanguageDetection(code=DEFAULT_LANGUAGE, confidence=0.0, matched_tokens=0)

    tokens = _tokens(text)
    if not tokens:
        return LanguageDetection(code=DEFAULT_LANGUAGE, confidence=0.0, matched_tokens=0)

    token_set = set(tokens)
    es_hits = len(token_set & _ES_STOPWORDS)
    en_hits = len(token_set & _EN_STOPWORDS)
    pt_hits = len(token_set & _PT_STOPWORDS)

    # Diacritics count as a single very strong signal even when the text
    # is short (e.g. "sí" vs "si").
    diacritic_hits = sum(1 for ch in text.lower() if ch in _ES_PT_DIACRITICS)

    # Weighted score — stop-word matches are noisy on single-word
    # utterances, diacritics are not.
    scores = {
        "es": es_hits * 1.0 + (pt_hits * 0.4) + (diacritic_hits * 1.5),
        "pt": pt_hits * 1.0 + (es_hits * 0.4) + (diacritic_hits * 1.5),
        "en": en_hits * 1.0,
    }

    best_code = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_code]
    total_score = sum(scores.values()) or 1.0

    if best_score < 0.5:
        # Not enough signal — return the configured default with low confidence.
        return LanguageDetection(
            code=DEFAULT_LANGUAGE,
            confidence=0.0,
            matched_tokens=int(best_score),
        )

    confidence = min(1.0, best_score / (total_score + 1.5))
    matched = (
        es_hits
        if best_code == "es"
        else pt_hits
        if best_code == "pt"
        else en_hits
    )
    return LanguageDetection(
        code=best_code,
        confidence=round(confidence, 3),
        matched_tokens=matched + diacritic_hits,
    )


def resolve_stt_language(
    *,
    explicit: Optional[str] = None,
    transcribed_text: Optional[str] = None,
    configured_default: Optional[str] = None,
) -> str:
    """Resolve the final STT language code, honouring all input sources.

    Priority:

    1. ``explicit`` — caller forced a specific language (e.g. user picked
       one in the UI or the wake-word grammar is language-specific).
    2. ``transcribed_text`` heuristic — used by the second pass where we
       already have a transcript and want to align the TTS response.
    3. ``configured_default`` — ``~/.openjarvis/config.yaml`` value.
    4. :data:`DEFAULT_LANGUAGE` (``"es"``).

    Returns a lowercase BCP-47 code that the STT backends understand.
    """
    if explicit:
        code = explicit.strip().lower()
        if code in SUPPORTED_LANGUAGES:
            return code
        # Allow short forms like "es-mx", "es_es" — collapse to base.
        base = code.split("-", 1)[0].split("_", 1)[0]
        if base in SUPPORTED_LANGUAGES:
            return base
        logger.debug("Unknown explicit language %r; falling back", explicit)

    if transcribed_text:
        detection = detect_language_from_text(transcribed_text)
        if detection.confidence >= 0.35:
            return detection.code

    if configured_default:
        code = configured_default.strip().lower()
        base = code.split("-", 1)[0].split("_", 1)[0]
        if base in SUPPORTED_LANGUAGES:
            return base

    return DEFAULT_LANGUAGE


def language_name(code: str) -> str:
    """Return the human-readable name of a language code, or the code itself."""
    meta = _LANGUAGE_META.get(code.split("-", 1)[0])
    if meta is None:
        return code
    return meta["name"]


def macos_voices_for(code: str) -> Iterable[str]:
    """Yield the recommended macOS ``say`` voices for a language code."""
    meta = _LANGUAGE_META.get(code.split("-", 1)[0])
    if meta is None:
        return ()
    return meta["macos_voices"]


def kokoro_voice_prefix(code: str) -> Optional[str]:
    """Return the Kokoro voice-ID prefix for *code*, or ``None`` if unsupported."""
    meta = _LANGUAGE_META.get(code.split("-", 1)[0])
    if meta is None:
        return None
    return meta["tts_prefix"]


def default_voice_for(code: str, backend: str) -> str:
    """Return a sensible default TTS voice id for *backend*/*code*.

    * ``kokoro`` → ``e<gender>_<name>`` style (e.g. ``ef_dora``)
    * ``openai`` / ``cartesia`` → use the ISO language code
    * ``macos_say`` → first recommended macOS voice
    """
    base = code.split("-", 1)[0]
    if backend == "kokoro":
        prefix = kokoro_voice_prefix(base)
        if prefix is None:
            return "af_heart"  # fall back to American English
        # Default female voice per language — Kokoro ships
        # ``ef_dora`` (es), ``pf_lumia`` (pt), ``ff_siwit`` (fr),
        # ``if_sara`` (it), ``zf_xiaoxiao`` (zh), ``jf_nezumi`` (ja),
        # ``af_heart`` (en).
        defaults = {
            "es": "ef_dora",
            "en": "af_heart",
            "pt": "pf_lumia",
            "fr": "ff_siwit",
            "it": "if_sara",
            "zh": "zf_xiaoxiao",
            "ja": "jf_nezumi",
        }
        return defaults.get(base, "af_heart")
    if backend == "macos_say":
        voices = list(macos_voices_for(base))
        return voices[0] if voices else ""
    # cloud backends take a bare code
    return base


__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "LanguageDetection",
    "default_voice_for",
    "detect_language_from_text",
    "kokoro_voice_prefix",
    "language_name",
    "macos_voices_for",
    "resolve_stt_language",
]
