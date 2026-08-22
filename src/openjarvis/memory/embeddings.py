"""Semantic search over a flat list of memories using sentence-transformers.

This module is the *high-level* retrieval layer that lives on top of the
embedder abstraction defined in
:mod:`openjarvis.tools.storage.embeddings`. Given a query string and a
list of memory strings, it ranks the memories by cosine similarity and
returns the top-k matches along with their scores.

The model defaults to ``paraphrase-multilingual-MiniLM-L12-v2`` because
OpenJarvis is a multilingual product and this checkpoint covers Spanish,
English and Portuguese out of the box while staying under 120 MB on disk.

The module is deliberately dependency-tolerant: importing
``sentence-transformers`` happens lazily so the rest of the package can
still be imported (and tests can still mock the import) on hosts where
the heavy ML dependency is not installed.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import numpy as np


_DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class SemanticMemory:
    """Rank a corpus of memory strings by semantic similarity to a query.

    Parameters
    ----------
    model_name:
        HuggingFace identifier of the sentence-transformer model to load.
        Defaults to a multilingual MiniLM so the assistant works in
        Spanish/English/Portuguese without a separate download.
    embedder:
        Optional pre-built embedder object. When provided we skip loading
        ``sentence-transformers`` entirely — useful for tests and for
        callers that already manage an embedder (e.g. the dense
        retrieval backend).
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        embedder: Optional[Any] = None,
    ) -> None:
        self._embedder = embedder
        self._model_name = model_name
        if self._embedder is None:
            try:
                from sentence_transformers import (  # type: ignore[import-not-found]
                    SentenceTransformer,
                )
            except ImportError as exc:  # pragma: no cover - import guard
                raise ImportError(
                    "sentence-transformers no instalado. "
                    "Instalar con: pip install sentence-transformers"
                ) from exc
            self._model = SentenceTransformer(model_name)
            self._owns_model = True
        else:
            self._model = self._embedder
            self._owns_model = False

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def encode(self, text: str) -> np.ndarray:
        """Encode a single string into a 1-D numpy vector."""
        if self._owns_model:
            vector = self._model.encode(text, convert_to_numpy=True)
        else:
            vector = np.asarray(self._model.embed([text])[0])
        return np.asarray(vector, dtype=np.float32)

    def _encode_batch(self, memories: List[str]) -> np.ndarray:
        if self._owns_model:
            vectors = self._model.encode(memories, convert_to_numpy=True)
        else:
            vectors = np.asarray(self._model.embed(memories))
        return np.asarray(vectors, dtype=np.float32)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def similarity(
        self,
        query: str,
        memories: List[str],
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """Return ``(index, score)`` pairs sorted by descending similarity.

        An empty corpus yields an empty list. We also guard against the
        degenerate "all-zero" edge case (e.g. the embedder returned a row
        of zeros) by treating it as zero similarity rather than emitting
        ``nan`` to downstream callers.
        """
        if not memories:
            return []
        if top_k <= 0:
            return []

        query_emb = self.encode(query)
        mem_embs = self._encode_batch(memories)

        scores = _cosine_scores(query_emb, mem_embs)
        scores = _safe_where_zero(query_emb, mem_embs, scores)

        ranked = sorted(enumerate(scores.tolist()), key=lambda x: -x[1])
        return ranked[:top_k]


def _cosine_scores(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between ``query`` and each row of ``matrix``."""
    query_norm = np.linalg.norm(query)
    if query_norm == 0.0:
        return np.zeros(matrix.shape[0], dtype=np.float32)
    row_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe_norms = np.where(row_norms == 0.0, 1.0, row_norms)
    normalized_query = query / query_norm
    normalized_matrix = matrix / safe_norms
    return (normalized_matrix @ normalized_query).astype(np.float32)


def _safe_where_zero(
    query: np.ndarray, matrix: np.ndarray, scores: np.ndarray
) -> np.ndarray:
    """Zero out rows whose embedding was all-zeros (degenerate case)."""
    zero_rows = np.all(matrix == 0.0, axis=1)
    if zero_rows.any():
        scores = scores.copy()
        scores[zero_rows] = 0.0
    return scores


def make_semantic_search(
    model_name: Optional[str] = None,
    embedder: Optional[Any] = None,
) -> Callable[[str, List[str], int], List[Tuple[int, float]]]:
    """Build a closure-style ``search`` function bound to a model.

    Returns
    -------
    Callable[[str, List[str], int], List[Tuple[int, float]]]
        A function ``search(query, memories, top_k=5)`` ready to be passed
        around without holding a reference to the ``SemanticMemory``
        instance.
    """
    sm = SemanticMemory(model_name or _DEFAULT_MODEL, embedder=embedder)

    def search(
        query: str,
        memories: List[str],
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        return sm.similarity(query, memories, top_k)

    return search


__all__ = (
    "SemanticMemory",
    "make_semantic_search",
)