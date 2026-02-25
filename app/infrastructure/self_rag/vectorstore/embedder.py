"""
vectorstore/embedder.py

Production-grade embedding wrapper for the Self-RAG vectorstore layer.
Wraps LangChain's HuggingFaceEmbeddings with validation, structured
logging, batching, and a simple cache to avoid re-embedding identical texts.

Pipeline position:
    TextSplitter → [Embedder] → VectorStore
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class Embedder:
    """
    Wraps LangChain's HuggingFaceEmbeddings with:
        - Lazy initialisation (model loads only on first use)
        - In-memory cache to avoid re-embedding identical texts
        - Batch embedding with configurable batch size
        - Structured logging with timing
        - Input validation

    The underlying model runs 100% locally via sentence-transformers.
    No API key or network call required after initial model download.

    Default model : all-MiniLM-L6-v2
        - 384-dimensional embeddings
        - ~22M parameters, very fast on CPU
        - Good general-purpose semantic similarity

    Usage
    -----
    embedder = Embedder()
    embedding_fn = embedder.get()          # pass to LocalVectorStore
    vectors = embedder.embed_texts(texts)  # embed a list of strings
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size:  int = 64,
        cache_size:  int = 1_000,
    ) -> None:
        self._model_name  = model_name
        self._batch_size  = batch_size
        self._cache_size  = cache_size

        # Lazy — model is not loaded until get() or embed_texts() is called
        self._model: Optional[HuggingFaceEmbeddings] = None

        # Simple in-memory cache: text_hash → embedding vector
        self._cache: dict[str, list[float]] = {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Load the sentence-transformers model (called once on first use)."""
        if self._model is not None:
            return

        logger.info("Loading embedding model: %s", self._model_name)
        start = time.perf_counter()

        self._model = HuggingFaceEmbeddings(model_name=self._model_name)

        elapsed = time.perf_counter() - start
        logger.info("Embedding model loaded in %.2fs", elapsed)

    @staticmethod
    def _hash(text: str) -> str:
        """Return an MD5 hash of the text (used as cache key)."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self) -> HuggingFaceEmbeddings:
        """
        Return the underlying HuggingFaceEmbeddings object.
        This is what LocalVectorStore accepts as its embedding_function.
        """
        self._load_model()
        return self._model  # type: ignore[return-value]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts, using the cache to skip already-seen texts.

        Args:
            texts: List of plain strings to embed.

        Returns:
            List of embedding vectors (one per input text).
        """
        if not texts:
            return []

        self._load_model()
        assert self._model is not None

        results: list[Optional[list[float]]] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts:   list[str] = []

        # Check cache first
        for i, text in enumerate(texts):
            key = self._hash(text)
            if key in self._cache:
                results[i] = self._cache[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Embed uncached texts in batches
        if uncached_texts:
            start = time.perf_counter()
            all_vectors: list[list[float]] = []

            for batch_start in range(0, len(uncached_texts), self._batch_size):
                batch = uncached_texts[batch_start : batch_start + self._batch_size]
                vectors = self._model.embed_documents(batch)
                all_vectors.extend(vectors)

            elapsed = time.perf_counter() - start
            logger.debug(
                "Embedded %d texts in %.2fs", len(uncached_texts), elapsed
            )

            # Store in cache and fill results
            for idx, vector in zip(uncached_indices, all_vectors):
                key = self._hash(texts[idx])
                # Evict oldest entry if cache is full
                if len(self._cache) >= self._cache_size:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[key] = vector
                results[idx] = vector

        return results  # type: ignore[return-value]