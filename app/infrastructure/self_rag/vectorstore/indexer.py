"""
vectorstore/indexer.py

Production-grade indexer for the Self-RAG pipeline.
Orchestrates the full ingestion pipeline:
    DocumentLoader → Preprocessor → TextSplitter → LocalVectorStore

This is the single command that takes raw files and produces a
searchable vector index — one call to index() or index_directory()
is all main.py needs.

Pipeline position:
    [Indexer] → LocalVectorStore (writes)
"""

from __future__ import annotations

import logging

from ..ingestion.document_loader import DocumentLoader
from ..ingestion.preprocessor    import Preprocessor
from ..ingestion.text_splitter   import TextSplitter
from .store                      import LocalVectorStore

logger = logging.getLogger(__name__)


class Indexer:
    """
    Orchestrates the complete ingestion → indexing pipeline.

    Components
    ----------
    DocumentLoader  → loads raw files from disk
    Preprocessor    → cleans, deduplicates, and enriches documents
    TextSplitter    → splits documents into smaller chunks
    LocalVectorStore→ embeds and stores chunks in ChromaDB

    Usage
    -----
    indexer = Indexer(text_splitter, vector_store)

    # Index a single file
    indexer.index("./docs/chapter1.pdf")

    # Index all files in a folder
    indexer.index_directory("./docs/")
    """

    def __init__(
        self,
        text_splitter: TextSplitter,
        vector_store:  LocalVectorStore,
    ) -> None:
        self._loader       = DocumentLoader()
        self._preprocessor = Preprocessor()
        self._splitter     = text_splitter
        self._store        = vector_store

    def index(self, file_path: str) -> None:
        """
        Full pipeline for a single file:
            load → preprocess → split → store.

        Args:
            file_path: Path to the document to index.
        """
        logger.info("=== Starting indexing: %s ===", file_path)

        raw_docs    = self._loader.load(file_path)
        clean_docs  = self._preprocessor.process(raw_docs)
        chunks, stats = self._splitter.split(clean_docs)

        if not chunks:
            logger.warning("No chunks produced from %s — nothing indexed.", file_path)
            return

        self._store.add_documents(chunks)

        logger.info(
            "=== Indexing complete: %s | %d chunks stored ===",
            file_path, stats.output_chunk_count,
        )

    def index_directory(self, directory: str) -> None:
        """
        Full pipeline for an entire directory of files.

        Args:
            directory: Path to folder containing documents.
        """
        logger.info("=== Starting directory indexing: %s ===", directory)

        raw_docs    = self._loader.load_directory(directory)
        clean_docs  = self._preprocessor.process(raw_docs)
        chunks, stats = self._splitter.split(clean_docs)

        if not chunks:
            logger.warning("No chunks produced from directory %s — nothing indexed.", directory)
            return

        self._store.add_documents(chunks)

        logger.info(
            "=== Directory indexing complete: %d chunks stored from %s ===",
            stats.output_chunk_count, directory,
        )
