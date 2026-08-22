"""Tests for openjarvis.memory.async_extractor (extract_memories)."""

from __future__ import annotations

from typing import List

import pytest

from openjarvis.memory.async_extractor import (
    ExtractedMemory,
    extract_memories,
)


class FakeLLM:
    """Stub LLMClient returning a canned response (or raising)."""

    def __init__(self, response: str = "", *, raises: Exception | None = None) -> None:
        self._response = response
        self._raises = raises
        self.calls: List[str] = []

    async def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self._raises is not None:
            raise self._raises
        return self._response


@pytest.mark.asyncio
async def test_parses_clean_json_array() -> None:
    """The happy path: a clean JSON array produces ExtractedMemory rows."""
    llm = FakeLLM(
        response=(
            '[{"content": "Le gusta el café", "category": "preference", '
            '"confidence": 0.9}]'
        )
    )
    out = await extract_memories(llm, "Usuario: me gusta el café")
    assert len(out) == 1
    assert out[0] == ExtractedMemory(
        content="Le gusta el café", category="preference", confidence=0.9
    )


@pytest.mark.asyncio
async def test_parses_array_wrapped_in_prose() -> None:
    """The extractor must find the array even when surrounded by chatter."""
    llm = FakeLLM(
        response=(
            'Sure!\nHere you go:\n'
            '[{"content": "Vive en Madrid", "category": "fact", "confidence": 0.8}]\n'
            "Bye."
        )
    )
    out = await extract_memories(llm, "...")
    assert len(out) == 1
    assert out[0].content == "Vive en Madrid"


@pytest.mark.asyncio
async def test_empty_array_returns_no_memories() -> None:
    """[] is the canonical "nothing to remember" answer."""
    llm = FakeLLM(response="[]")
    out = await extract_memories(llm, "Hola, ¿qué tal?")
    assert out == []


@pytest.mark.asyncio
async def test_invalid_json_returns_empty() -> None:
    """Garbage in, garbage out — never raise, just return []."""
    llm = FakeLLM(response="I don't know how to answer")
    out = await extract_memories(llm, "...")
    assert out == []


@pytest.mark.asyncio
async def test_unknown_category_is_replaced() -> None:
    """A bogus category value is replaced with the literal 'default'."""
    llm = FakeLLM(
        response=(
            '[{"content": "Hecho X", "category": "mystery", "confidence": 0.5}]'
        )
    )
    out = await extract_memories(llm, "...")
    assert out[0].category == "default"


@pytest.mark.asyncio
async def test_confidence_is_clamped() -> None:
    """Out-of-range confidence values are clamped to [0.0, 1.0]."""
    llm_high = FakeLLM(
        response='[{"content": "a", "category": "fact", "confidence": 5.0}]'
    )
    out_high = await extract_memories(llm_high, "...")
    assert out_high[0].confidence == 1.0

    llm_low = FakeLLM(
        response='[{"content": "b", "category": "fact", "confidence": -3.0}]'
    )
    out_low = await extract_memories(llm_low, "...")
    assert out_low[0].confidence == 0.0


@pytest.mark.asyncio
async def test_missing_content_is_skipped() -> None:
    """Entries without a non-empty ``content`` string are dropped."""
    llm = FakeLLM(
        response=(
            '[{"category": "fact", "confidence": 0.5}, '
            '{"content": "ok", "category": "fact", "confidence": 0.7}]'
        )
    )
    out = await extract_memories(llm, "...")
    assert len(out) == 1
    assert out[0].content == "ok"


@pytest.mark.asyncio
async def test_llm_exception_returns_empty() -> None:
    """A failing LLM call must not propagate — best-effort semantics."""
    llm = FakeLLM(raises=RuntimeError("upstream is down"))
    out = await extract_memories(llm, "...")
    assert out == []


@pytest.mark.asyncio
async def test_long_conversation_is_truncated() -> None:
    """The conversation passed to the LLM is sliced to ``max_chars``."""
    # Use a marker character that never appears in the prompt template.
    long_text = "Z" * 10_000
    llm = FakeLLM(response="[]")
    await extract_memories(llm, long_text, max_chars=100)
    # The prompt template wraps the conversation in <conversation>...</conversation>
    prompt = llm.calls[0]
    assert prompt.count("Z") == 100


@pytest.mark.asyncio
async def test_multiple_memories_preserved() -> None:
    """All well-formed entries are returned in order."""
    llm = FakeLLM(
        response=(
            '['
            '{"content": "a", "category": "fact", "confidence": 0.9},'
            '{"content": "b", "category": "preference", "confidence": 0.7},'
            '{"content": "c", "category": "event", "confidence": 0.6}'
            ']'
        )
    )
    out = await extract_memories(llm, "...")
    assert [m.content for m in out] == ["a", "b", "c"]
    assert [m.category for m in out] == ["fact", "preference", "event"]