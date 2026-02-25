"""
ingestion/text_splitter.py

Production-grade text splitter for the Self-RAG ingestion pipeline.
Wraps LangChain's RecursiveCharacterTextSplitter with validation,
structured logging, chunk-quality filtering, and metadata propagation.

Pipeline position:
    DocumentLoader → Preprocessor → [TextSplitter] → Embedder → VectorStore
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@dataclass
class SplitStats:
    """Summary statistics returned alongside the chunks."""
    input_doc_count:  int
    output_chunk_count: int
    filtered_count:   int   # chunks dropped for being too short
    avg_chunk_chars:  float


class TextSplitter:
    """
    Wraps LangChain's RecursiveCharacterTextSplitter with production-grade
    validation, logging, chunk-quality filtering, and metadata enrichment.

    RecursiveCharacterTextSplitter splits on natural boundaries in order:
        paragraph (\\n\\n) → line (\\n) → sentence (". ") → word (" ") → char ("")

    This means chunks respect semantic boundaries as much as possible
    before falling back to hard character splits.

    Usage
    -----
    splitter = TextSplitter(chunk_size=512, chunk_overlap=64)
    chunks, stats = splitter.split(preprocessed_documents)
    """

    # Minimum number of characters a chunk must have to be kept.
    MIN_CHUNK_CHARS = 50

    def __init__(
        self,
        chunk_size:    int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Split on semantic boundaries first
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._chunk_size    = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, documents: list[Document]) -> tuple[list[Document], SplitStats]:
        """
        Split a list of preprocessed Documents into smaller chunks.

        Args:
            documents: Cleaned Documents from the Preprocessor.

        Returns:
            A tuple of:
                - chunks : List of Document chunks ready for embedding
                - stats  : SplitStats with counts and averages
        """
        if not documents:
            logger.warning("TextSplitter received an empty document list.")
            return [], SplitStats(0, 0, 0, 0.0)

        logger.info(
            "Splitting %d documents (chunk_size=%d, overlap=%d)...",
            len(documents), self._chunk_size, self._chunk_overlap,
        )

        # Split all documents
        raw_chunks: list[Document] = self._splitter.split_documents(documents)

        # Filter out very short chunks (noise, headers, page numbers, etc.)
        good_chunks: list[Document] = []
        filtered_count = 0

        for i, chunk in enumerate(raw_chunks):
            if len(chunk.page_content.strip()) < self.MIN_CHUNK_CHARS:
                logger.debug("Filtered short chunk (%d chars)", len(chunk.page_content))
                filtered_count += 1
                continue
            # Add chunk index to metadata for traceability
            chunk.metadata["chunk_index"] = i
            good_chunks.append(chunk)

        # Compute average chunk size
        avg_chars = (
            sum(len(c.page_content) for c in good_chunks) / len(good_chunks)
            if good_chunks else 0.0
        )

        stats = SplitStats(
            input_doc_count=len(documents),
            output_chunk_count=len(good_chunks),
            filtered_count=filtered_count,
            avg_chunk_chars=round(avg_chars, 1),
        )

        logger.info(
            "Split complete: %d chunks produced, %d filtered. Avg chunk: %.0f chars.",
            stats.output_chunk_count, stats.filtered_count, stats.avg_chunk_chars,
        )
        return good_chunks, stats
