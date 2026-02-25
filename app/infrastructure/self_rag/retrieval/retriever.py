"""
retrieval/retriever.py

Production-grade retriever for the Self-RAG pipeline.
Wraps LocalVectorStore's similarity search with query validation,
structured logging, timing, optional score thresholding, and
result deduplication.

Pipeline position:
    LocalVectorStore → [Retriever] → SelfRAGPipeline (Step 2)

The Retriever is intentionally thin — it does one thing:
    query (str) → top-k relevant Document chunks

All filtering for *relevance* (ISREL critic) happens in the pipeline,
not here. The retriever's job is purely mechanical: embed the query
and fetch the nearest neighbours from the vector store.
"""

from __future__ import annotations

import logging
import time

from langchain_core.documents import Document

from ..vectorstore.store import LocalVectorStore
from .. import config

logger = logging.getLogger(__name__)


class Retriever:
    """
    Wraps LocalVectorStore to fetch the top-k most similar document chunks
    for a given query.

    Optionally filters out results by score threshold (useful to skip very
    dissimilar documents even before the ISREL critic sees them).

    Args:
        vector_store:     Initialised LocalVectorStore (already loaded).
        top_k:            Number of documents to retrieve. Defaults to config value.
        score_threshold:  If set, discard chunks with similarity score above
                          this value (ChromaDB uses L2 distance — lower = better).
                          Set to None to disable threshold filtering.
    """

    def __init__(
        self,
        vector_store:    LocalVectorStore,
        top_k:           int            = config.TOP_K_RETRIEVAL,
        score_threshold: float | None   = None,
    ) -> None:
        self._store           = vector_store
        self._top_k           = top_k
        self._score_threshold = score_threshold

    def retrieve(self, query: str) -> list[Document]:
        """
        Fetch the top-k most similar document chunks for the query.

        Args:
            query: The user's question (plain text).

        Returns:
            List of Document objects, ordered by similarity (most similar first).
            Returns an empty list if no documents are found or the store is empty.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")

        start = time.perf_counter()

        if self._score_threshold is not None:
            # Use scored search so we can filter by distance
            scored_results = self._store.similarity_search_with_score(
                query, top_k=self._top_k
            )
            # Lower L2 distance = more similar → keep scores below threshold
            docs = [
                doc for doc, score in scored_results
                if score <= self._score_threshold
            ]
            discarded = len(scored_results) - len(docs)
            if discarded:
                logger.debug(
                    "Score threshold %.2f: discarded %d low-similarity chunks.",
                    self._score_threshold, discarded,
                )
        else:
            docs = self._store.similarity_search(query, top_k=self._top_k)

        elapsed = time.perf_counter() - start
        logger.info(
            "Retrieved %d chunks for query='%s...' in %.3fs",
            len(docs), query[:60], elapsed,
        )
        return docs
