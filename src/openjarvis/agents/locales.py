"""Resolve a localised system prompt base for an agent.

OpenJarvis ships with built-in Spanish/English base prompts under
``openjarvis/agents/locales/<lang>/system_base.md``. Agents can either
use the base directly (the most common path) or stack their own
agent-specific instructions on top of it.

The lookup order is:

1. ``openjarvis/agents/locales/<lang>/system_base.md`` (bundled)
2. ``$OPENJARVIS_HOME/agents/<name>/system_prompt.<lang>.md`` (user override)
3. ``$OPENJARVIS_HOME/agents/<name>/system_prompt.md`` (user default)

The helpers here are intentionally tiny — they don't try to render
templates. The agent itself does the final composition.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from openjarvis.speech.language import DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"


@lru_cache(maxsize=16)
def _read_locale(language: str) -> Optional[str]:
    """Read the bundled locale file for *language*, with caching."""
    path = _LOCALES_DIR / language / "system_base.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Failed to read bundled locale %s", path, exc_info=True)
        return None


def load_locale_system_base(language: Optional[str] = None) -> str:
    """Return the bundled system-base prompt for *language*.

    Falls back to :data:`DEFAULT_LANGUAGE` (``"es"``) and finally to the
    bundled English prompt so the function always returns a non-empty string.
    """
    language = (language or DEFAULT_LANGUAGE).lower().split("-", 1)[0]

    prompt = _read_locale(language)
    if prompt is not None:
        return prompt

    if language != DEFAULT_LANGUAGE:
        prompt = _read_locale(DEFAULT_LANGUAGE)
        if prompt is not None:
            return prompt

    # Last-ditch: bundled English. If even that's missing (corrupted
    # install) raise so the caller knows the bundle is broken.
    prompt = _read_locale("en")
    if prompt is None:
        raise FileNotFoundError(
            "No bundled locale prompts found under %s" % _LOCALES_DIR
        )
    return prompt


def list_available_languages() -> list[str]:
    """Return the list of language codes that ship with a bundled prompt."""
    if not _LOCALES_DIR.exists():
        return []
    return sorted(p.name for p in _LOCALES_DIR.iterdir() if p.is_dir())


__all__ = ["list_available_languages", "load_locale_system_base"]
