"""
infrastructure/services/note_indexing_service.py

Service responsible for indexing a note file into the Self-RAG vector store.

Called after a note is saved to disk.  It runs the file through the full
Self-RAG ingestion pipeline:
    DocumentLoader → Preprocessor → TextSplitter → LocalVectorStore

Design principles
-----------------
- Lazy imports: heavy ML libraries (HuggingFace, ChromaDB) are imported the
  FIRST time index() is called, NOT at server startup. This keeps startup fast.
- Non-blocking: if indexing fails the note upload is not affected (error is logged).
- Single responsibility: one method, one job.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NoteIndexingService:
    """
    Indexes a single file into the Self-RAG vector store.

    Lazy-loaded — the embedding model and ChromaDB client are created on the
    first call to index(), not when the class is instantiated. This means
    importing NoteIndexingService at the top of note_router.py adds near-zero
    startup overhead.

    Usage
    -----
    service = NoteIndexingService()
    service.index("/absolute/path/to/file.pdf")
    """

    def __init__(self) -> None:
        # All components are None until the first index() call
        self._loader       = None
        self._preprocessor = None
        self._splitter     = None
        self._store        = None

    # ------------------------------------------------------------------
    # Lazy setup (called once on first use)
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        """
        Import and initialise all RAG components.
        Called lazily on the first index() call so server startup stays fast.
        """
        if self._loader is not None:
            return  # already initialised

        # Local imports — these are expensive, so we defer them
        from ..self_rag.ingestion.document_loader import DocumentLoader
        from ..self_rag.ingestion.preprocessor    import Preprocessor
        from ..self_rag.ingestion.text_splitter   import TextSplitter
        from ..self_rag.vectorstore.embedder      import Embedder
        from ..self_rag.vectorstore.store         import LocalVectorStore
        from ..self_rag                           import config

        logger.info("[NoteIndexingService] Initialising RAG components (first-time setup)...")

        embedder = Embedder(model_name=config.EMBEDDING_MODEL)

        self._loader       = DocumentLoader()
        self._preprocessor = Preprocessor()
        self._splitter     = TextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
        self._store = LocalVectorStore(
            embedding_function=embedder.get(),
            persist_directory=config.VECTOR_STORE_PATH,
        )
        logger.info("[NoteIndexingService] RAG components ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self, file_path: str) -> None:
        """
        Run the full ingestion pipeline for a single file.

        Steps:
            1. Load  — file → LangChain Documents
            2. Clean — unicode normalise, deduplicate, enrich metadata
            3. Split — RecursiveCharacterTextSplitter into fixed-size chunks
            4. Store — embed + persist to ChromaDB

        Args:
            file_path: Absolute path to the file on disk.

        Note:
            Errors are caught and logged — this method never raises so the
            note upload response is never blocked by indexing failures.
        """
        try:
            self._setup()   # no-op after the first call

            logger.info("[NoteIndexingService] Indexing: %s", file_path)

            raw_docs   = self._loader.load(file_path)
            clean_docs = self._preprocessor.process(raw_docs)
            chunks, stats = self._splitter.split(clean_docs)

            if not chunks:
                logger.warning(
                    "[NoteIndexingService] No chunks from %s — skipped.", file_path
                )
                return

            self._store.add_documents(chunks)
            logger.info(
                "[NoteIndexingService] Done: %s | %d chunks stored",
                file_path, stats.output_chunk_count,
            )

        except Exception as exc:
            logger.error(
                "[NoteIndexingService] Failed to index %s: %s",
                file_path, exc, exc_info=True,
            )
