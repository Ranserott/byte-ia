"""Tests for openjarvis.memory.embeddings (SemanticMemory / make_semantic_search).

These tests deliberately use a fake embedder — they never hit the
sentence-transformers model. The dependency is optional at runtime, and
we want the suite to pass on a vanilla CI host.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pytest

from openjarvis.memory.embeddings import (
    SemanticMemory,
    make_semantic_search,
)


class FakeEmbedder:
    """Deterministic embedder that maps each word to a one-hot vector.

    Sentences sharing a vocabulary get high cosine similarity; sentences
    sharing nothing get near-zero scores. That gives us a controlled
    similarity signal we can assert on without a real model.
    """

    def __init__(self, vocab: List[str]) -> None:
        self.vocab = {word: idx for idx, word in enumerate(vocab)}

    def dim(self) -> int:
        return len(self.vocab)

    def embed(self, texts: List[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), len(self.vocab)), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in text.lower().split():
                idx = self.vocab.get(word)
                if idx is not None:
                    matrix[row, idx] = 1.0
        return matrix


@pytest.fixture()
def fake_embedder() -> FakeEmbedder:
    """Build a small English/Spanish vocab shared by the test sentences."""
    return FakeEmbedder(
        vocab=["i", "love", "coffee", "me", "gusta", "el", "café", "los", "tacos"]
    )


@pytest.fixture()
def sm(fake_embedder: FakeEmbedder) -> SemanticMemory:
    """Construct a SemanticMemory backed by the fake embedder."""
    return SemanticMemory(embedder=fake_embedder)


def test_similarity_returns_top_k_indices(sm: SemanticMemory) -> None:
    """The top hit for 'coffee' should mention coffee, not tacos."""
    memories = [
        "me gusta el café",
        "amo los tacos",
        "i love coffee",
    ]
    ranked = sm.similarity("coffee", memories, top_k=2)
    assert len(ranked) == 2
    # Higher index = better rank. Top-1 must be one of the coffee memories.
    assert ranked[0][0] in {0, 2}
    assert all(isinstance(score, float) for _, score in ranked)


def test_similarity_empty_corpus(sm: SemanticMemory) -> None:
    """Empty memory list yields empty result."""
    assert sm.similarity("anything", [], top_k=5) == []


def test_similarity_zero_top_k(sm: SemanticMemory) -> None:
    """top_k=0 must short-circuit to an empty result."""
    assert sm.similarity("anything", ["x"], top_k=0) == []


def test_similarity_scores_are_normalized(sm: SemanticMemory) -> None:
    """Cosine scores are in [-1, 1] for our one-hot vocab."""
    ranked = sm.similarity("coffee", ["i love coffee", "me gusta el café"])
    for _, score in ranked:
        assert -1.0 <= score <= 1.0


def test_similarity_handles_zero_vectors(fake_embedder: FakeEmbedder) -> None:
    """A memory the embedder maps to zeros scores 0, not nan."""
    sm = SemanticMemory(embedder=fake_embedder)
    ranked = sm.similarity("coffee", ["unseenword"])
    assert ranked == [(0, 0.0)]


def test_make_semantic_search_returns_callable(
    fake_embedder: FakeEmbedder,
) -> None:
    """``make_semantic_search`` returns a working closure."""
    search = make_semantic_search(embedder=fake_embedder)
    assert callable(search)
    ranked = search("coffee", ["i love coffee", "me gusta los tacos"], top_k=1)
    assert ranked[0][0] == 0


def test_constructor_without_embedder_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Instantiating without an embedder requires sentence-transformers.

    We force the import to fail and assert the friendly error message.
    """

    def _fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "sentence_transformers" or name.startswith(
            "sentence_transformers."
        ):
            raise ImportError("simulated missing dependency")
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", _fake_import)
    with pytest.raises(ImportError, match="sentence-transformers"):
        SemanticMemory()