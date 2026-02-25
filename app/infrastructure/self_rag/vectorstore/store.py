"""
vectorstore/store.py

Production-grade local vector store for the Self-RAG pipeline.
Wraps LangChain's Chroma integration with persistent local storage,
structured logging, metadata filtering, and safe initialisation.

Pipeline position:
    Embedder → [LocalVectorStore] ← Retriever
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

logger = logging.getLogger(__name__)


class LocalVectorStore:
    """
    Persistent local vector store backed by ChromaDB via LangChain.

    ChromaDB persists automatically to disk on every write — no explicit
    save() call needed. On restart, call load_existing() to reload the
    collection from disk instead of re-embedding all documents.

    Features
    --------
    - Auto-persist on every add_documents() call (ChromaDB default)
    - load_existing() to reload without re-indexing
    - similarity_search() with optional metadata filters
    - similarity_search_with_score() for ranked retrieval
    - as_retriever() to get a LangChain-native retriever for use in chains
    - collection_exists() for pre-flight checks in main.py / Indexer
    - delete_collection() for clean reindex workflows
    - document_count() for monitoring

    Usage
    -----
    embedder  = Embedder()
    store     = LocalVectorStore(embedder.get(), "./vectorstore/local_db")

    # First run — index documents
    store.add_documents(chunks)

    # Subsequent runs — reload from disk (no re-embedding)
    store.load_existing()
    docs = store.similarity_search("my query", top_k=5)
    """

    def __init__(
        self,
        embedding_function: Any,
        persist_directory:  str,
        collection_name:    str = "self_rag_docs",
    ) -> None:
        self._embedding_fn       = embedding_function
        self._persist_dir        = str(Path(persist_directory))
        self._collection_name    = collection_name
        self._db: Optional[Chroma] = None   # populated by add_documents() or load_existing()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Raise a clear error if the store has not been initialised yet."""
        if self._db is None:
            raise RuntimeError(
                "Vector store is not initialised. "
                "Call add_documents() for a first run or load_existing() on restart."
            )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_documents(self, documents: list[Document]) -> None:
        """
        Embed and store documents in ChromaDB.

        On first call this creates the collection.
        On subsequent calls it APPENDS to the existing collection.
        ChromaDB auto-persists every write to disk.

        Args:
            documents: List of LangChain Document objects (already chunked).
        """
        if not documents:
            logger.warning("add_documents called with an empty list — nothing stored.")
            return

        logger.info("Indexing %d document chunks into ChromaDB...", len(documents))
        start = time.perf_counter()

        self._db = Chroma.from_documents(
            documents=documents,
            embedding=self._embedding_fn,
            collection_name=self._collection_name,
            persist_directory=self._persist_dir,
        )

        elapsed = time.perf_counter() - start
        logger.info(
            "Indexed %d chunks in %.2fs — persisted to %s",
            len(documents), elapsed, self._persist_dir,
        )

    def delete_collection(self) -> None:
        """
        Delete the entire ChromaDB collection from disk.
        Use this before a full re-index to ensure a clean slate.
        """
        self._ensure_loaded()
        assert self._db is not None
        self._db.delete_collection()
        self._db = None
        logger.warning("Deleted collection '%s' from %s", self._collection_name, self._persist_dir)

    # ------------------------------------------------------------------
    # Read / load operations
    # ------------------------------------------------------------------

    def load_existing(self) -> None:
        """
        Reload an existing ChromaDB collection from disk WITHOUT re-embedding.

        Call this on application restart when documents are already indexed.
        Raises RuntimeError if no collection is found on disk.
        """
        if not os.path.exists(self._persist_dir):
            raise RuntimeError(
                f"Vector store directory not found: {self._persist_dir}. "
                "Run the indexer first to create it."
            )

        logger.info("Loading existing vector store from %s", self._persist_dir)
        start = time.perf_counter()

        self._db = Chroma(
            collection_name=self._collection_name,
            embedding_function=self._embedding_fn,
            persist_directory=self._persist_dir,
        )

        elapsed = time.perf_counter() - start
        logger.info(
            "Vector store loaded in %.2fs (%d documents)",
            elapsed, self.document_count(),
        )

    def collection_exists(self) -> bool:
        """
        Return True if a persisted ChromaDB collection exists on disk.
        Used in main.py / Indexer to decide whether to index or load.
        """
        return os.path.exists(self._persist_dir)

    # ------------------------------------------------------------------
    # Search operations
    # ------------------------------------------------------------------

    def similarity_search(
        self,
        query:   str,
        top_k:   int = 5,
        filter:  Optional[dict[str, Any]] = None,   # e.g. {"source": "chapter1.pdf"}
    ) -> list[Document]:
        """
        Return the top-k most similar documents for a query string.

        Args:
            query:  The user's question (plain text).
            top_k:  Number of results to return.
            filter: Optional ChromaDB metadata filter dict.

        Returns:
            List of Document objects ordered by similarity (most similar first).
        """
        self._ensure_loaded()
        assert self._db is not None

        start = time.perf_counter()
        results = self._db.similarity_search(query, k=top_k, filter=filter)
        elapsed = time.perf_counter() - start

        logger.debug(
            "similarity_search: %d results for query='%s...' in %.3fs",
            len(results), query[:60], elapsed,
        )
        return results

    def similarity_search_with_score(
        self,
        query:  str,
        top_k:  int = 5,
        filter: Optional[dict[str, Any]] = None,
    ) -> list[tuple[Document, float]]:
        """
        Return the top-k documents together with their similarity scores.

        Returns:
            List of (Document, score) tuples. Lower score = more similar in
            ChromaDB's L2 distance mode; higher = more similar in cosine mode.
        """
        self._ensure_loaded()
        assert self._db is not None

        return self._db.similarity_search_with_score(query, k=top_k, filter=filter)

    def as_retriever(
        self,
        top_k: int = 5,
        filter: Optional[dict[str, Any]] = None,
    ) -> VectorStoreRetriever:
        """
        Return a LangChain-native VectorStoreRetriever.
        Use this when you want to plug the store into a LangChain LCEL chain.
        """
        self._ensure_loaded()
        assert self._db is not None

        search_kwargs: dict[str, Any] = {"k": top_k,"fetch_k": 20}
        if filter:
            search_kwargs["filter"] = filter

        return self._db.as_retriever(search_type="mmr" , search_kwargs=search_kwargs)

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def document_count(self) -> int:
        """Return the number of document chunks stored in the collection."""
        if self._db is None:
            return 0
        return self._db._collection.count()  # ChromaDB internal API
