"""
ingestion/preprocessor.py

Production-grade document preprocessor for the Self-RAG ingestion pipeline.
Handles text cleaning, deduplication, and metadata enrichment before
documents are passed to the text splitter.

Pipeline position:
    DocumentLoader → [Preprocessor] → TextSplitter → Embedder → VectorStore
"""

import hashlib
import logging
import re
import unicodedata

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class Preprocessor:
    """
    Cleans, deduplicates, and enriches LangChain Documents before chunking.

    What it does
    ------------
    1. clean()       : Remove noise from raw text (control chars, extra whitespace, etc.)
    2. deduplicate() : Drop documents whose content is identical (by MD5 hash)
    3. enrich()      : Add useful metadata fields (source_file, char_count, content_hash)
    4. process()     : Run all three steps in one call — this is the main entry point

    Usage
    -----
    preprocessor = Preprocessor()
    clean_docs   = preprocessor.process(raw_docs)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, documents: list[Document]) -> list[Document]:
        """
        Full preprocessing pipeline: clean → deduplicate → enrich.

        Args:
            documents: Raw Document objects from DocumentLoader.

        Returns:
            Cleaned, deduplicated, and metadata-enriched Documents.
        """
        logger.info("Preprocessing %d raw documents...", len(documents))

        docs = self._clean_all(documents)
        docs = self._deduplicate(docs)
        docs = self._enrich_all(docs)

        logger.info("Preprocessing complete: %d documents remaining.", len(docs))
        return docs

    # ------------------------------------------------------------------
    # Step 1 — Clean
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """
        Clean raw text extracted from a document:
        - Normalise unicode to NFC form
        - Remove non-printable / control characters
        - Replace multiple newlines with two newlines (preserve paragraphs)
        - Collapse excessive whitespace (spaces/tabs) into a single space
        - Strip leading/trailing whitespace
        """
        # 1. Normalise unicode (e.g. é = e + combining accent → single char)
        text = unicodedata.normalize("NFC", text)

        # 2. Remove control characters (except newline \n and tab \t)
        text = "".join(
            ch for ch in text
            if unicodedata.category(ch) != "Cc" or ch in ("\n", "\t")
        )

        # 3. Collapse 3+ consecutive newlines into 2 (preserve paragraph breaks)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 4. Replace tabs with a single space
        text = text.replace("\t", " ")

        # 5. Collapse multiple spaces into one
        text = re.sub(r" {2,}", " ", text)

        # 6. Strip
        return text.strip()

    def _clean_all(self, documents: list[Document]) -> list[Document]:
        """Apply _clean_text to every document; drop empty results."""
        cleaned: list[Document] = []

        for doc in documents:
            clean_text = self._clean_text(doc.page_content)
            if not clean_text:
                logger.debug("Dropped empty document from source: %s", doc.metadata.get("source"))
                continue
            doc.page_content = clean_text
            cleaned.append(doc)

        logger.debug("After cleaning: %d / %d documents kept.", len(cleaned), len(documents))
        return cleaned

    # ------------------------------------------------------------------
    # Step 2 — Deduplicate
    # ------------------------------------------------------------------

    @staticmethod
    def _content_hash(text: str) -> str:
        """MD5 hash of the document text — used as a deduplication key."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _deduplicate(self, documents: list[Document]) -> list[Document]:
        """
        Remove documents whose page_content is identical to one already seen.
        Comparison is done by MD5 hash (not full string compare) for speed.
        """
        seen_hashes: set[str] = set()
        unique_docs: list[Document] = []

        for doc in documents:
            h = self._content_hash(doc.page_content)
            if h in seen_hashes:
                logger.debug("Duplicate removed: %s", doc.metadata.get("source", "unknown"))
                continue
            seen_hashes.add(h)
            unique_docs.append(doc)

        removed = len(documents) - len(unique_docs)
        if removed:
            logger.info("Removed %d duplicate document(s).", removed)

        return unique_docs

    # ------------------------------------------------------------------
    # Step 3 — Enrich metadata
    # ------------------------------------------------------------------

    def _enrich(self, doc: Document) -> Document:
        """
        Add extra metadata fields to a Document:
        - content_hash  : MD5 of page_content (useful for change detection)
        - char_count    : Character count of the cleaned text
        - word_count    : Approximate word count
        """
        doc.metadata["content_hash"] = self._content_hash(doc.page_content)
        doc.metadata["char_count"]   = len(doc.page_content)
        doc.metadata["word_count"]   = len(doc.page_content.split())
        return doc

    def _enrich_all(self, documents: list[Document]) -> list[Document]:
        """Apply _enrich to every document."""
        return [self._enrich(doc) for doc in documents]
