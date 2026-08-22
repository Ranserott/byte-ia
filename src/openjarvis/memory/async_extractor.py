"""Async, JSON-object extractor for conversational memory.

This module complements the synchronous, string-list :class:`FactExtractor`
already shipped at :mod:`openjarvis.memory.extractor`. Where that extractor
returns ``List[str]`` (one fact per element) and is meant to be called from
the in-process memory worker, this one is designed for chat backends that
talk to an LLM over ``async`` HTTP and want structured records with a
``category`` and a ``confidence`` score.

Both modules coexist intentionally — they target different runtimes and
return different shapes. Code that needs the rich record just imports
from here; the existing memory service keeps using :class:`FactExtractor`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, List, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractedMemory:
    """A single durable fact extracted from a conversation.

    Attributes
    ----------
    content:
        The fact itself, in natural language (Spanish by default).
    category:
        One of ``"preference"``, ``"fact"``, or ``"event"`` — used by
        downstream stores to bucket memories for retrieval.
    confidence:
        Model-reported confidence in ``[0.0, 1.0]``. Downstream code
        typically treats anything below a configurable threshold as
        noise.
    """

    content: str
    category: str
    confidence: float


EXTRACT_PROMPT = """Analiza esta conversación y extrae hechos importantes para recordar del usuario:

<conversation>
{conversation}
</conversation>

Devuelve un JSON array con objetos que tengan:
- content: el hecho o preferencia (en español)
- category: "preference" | "fact" | "event"
- confidence: 0.0 - 1.0

Si no hay nada importante, devuelve [].
Responde SOLO con JSON válido, nada más."""


class LLMClient(Protocol):
    """Minimal protocol an LLM client must satisfy for this extractor."""

    async def complete(self, prompt: str) -> str:
        """Return the raw text completion for ``prompt``."""
        ...


_VALID_CATEGORIES = frozenset({"preference", "fact", "event"})


def _coerce_category(raw: Any) -> str:
    """Return a known category string or ``"default"`` if the model lied."""
    if not isinstance(raw, str):
        return "default"
    lowered = raw.strip().lower()
    return lowered if lowered in _VALID_CATEGORIES else "default"


def _coerce_confidence(raw: Any) -> float:
    """Clamp the model's confidence to ``[0.0, 1.0]``."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.5
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _parse_json_array(response: str) -> List[ExtractedMemory]:
    """Extract the first JSON array from ``response`` and parse it.

    Returns an empty list when no array can be located or decoded — the
    extractor is best-effort and must never crash the caller.
    """
    json_match = re.search(r"\[.*?\]", response, re.DOTALL)
    if not json_match:
        return []
    try:
        data = json.loads(json_match.group(0))
    except (json.JSONDecodeError, ValueError):
        logger.debug("Memory extractor: invalid JSON from LLM", exc_info=True)
        return []
    if not isinstance(data, list):
        return []

    memories: List[ExtractedMemory] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        content = entry.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        memories.append(
            ExtractedMemory(
                content=content.strip(),
                category=_coerce_category(entry.get("category", "fact")),
                confidence=_coerce_confidence(entry.get("confidence", 0.5)),
            )
        )
    return memories


async def extract_memories(
    llm_client: LLMClient,
    conversation: str,
    *,
    max_chars: int = 3000,
) -> List[ExtractedMemory]:
    """Run the extraction prompt against ``llm_client`` and parse the JSON.

    Parameters
    ----------
    llm_client:
        Anything implementing :class:`LLMClient` (an async ``complete``
        method that returns a string).
    conversation:
        The full conversation text. We slice to ``max_chars`` before
        sending so a runaway transcript never blows past the model's
        context window.
    max_chars:
        Upper bound on the prompt size; defaults to 3000 which fits
        comfortably inside any small local model's window with the
        system prompt overhead.

    Returns
    -------
    list[ExtractedMemory]
        May be empty — the caller decides whether to persist.
    """
    truncated = conversation[:max_chars]
    prompt = EXTRACT_PROMPT.format(conversation=truncated)

    try:
        response = await llm_client.complete(prompt)
    except Exception:  # noqa: BLE001 — extraction is best-effort
        logger.debug("Memory extractor: LLM call failed", exc_info=True)
        return []

    return _parse_json_array(response)


__all__ = (
    "ExtractedMemory",
    "EXTRACT_PROMPT",
    "LLMClient",
    "extract_memories",
)