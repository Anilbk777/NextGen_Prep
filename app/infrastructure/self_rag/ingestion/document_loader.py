"""
ingestion/document_loader.py

Loads raw files (PDF, Word, PowerPoint) and returns LangChain Document objects.

Pipeline position:
    [DocumentLoader] → Preprocessor → TextSplitter → Embedder → VectorStore
"""

import os
import logging

from langchain_community.document_loaders import (
    UnstructuredPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
)
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Loads documents from disk into LangChain Document objects.

    Supported formats
    -----------------
    .pdf   → UnstructuredPDFLoader
    .doc   → UnstructuredWordDocumentLoader
    .docx  → UnstructuredWordDocumentLoader
    .ppt   → UnstructuredPowerPointLoader
    .pptx  → UnstructuredPowerPointLoader

    Usage
    -----
    loader = DocumentLoader()
    docs   = loader.load("/path/to/file.pdf")
    docs   = loader.load_directory("/path/to/folder")
    """

    # Maps file extensions to their LangChain loader classes
    SUPPORTED_LOADERS = {
        ".pdf":  UnstructuredPDFLoader,
        ".doc":  UnstructuredWordDocumentLoader,
        ".docx": UnstructuredWordDocumentLoader,
        ".ppt":  UnstructuredPowerPointLoader,
        ".pptx": UnstructuredPowerPointLoader,
    }

    def load(self, file_path: str) -> list[Document]:
        """
        Load a single file and return a list of Documents.

        Args:
            file_path: Absolute or relative path to the file.

        Returns:
            List of Document objects (one or more per file, depending on loader).

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError:        If the file extension is not supported.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = os.path.splitext(file_path)[1].lower()
        loader_class = self.SUPPORTED_LOADERS.get(extension)

        if loader_class is None:
            raise ValueError(
                f"Unsupported file type: '{extension}'. "
                f"Supported types: {list(self.SUPPORTED_LOADERS.keys())}"
            )

        logger.info("Loading file: %s", file_path)
        loader = loader_class(file_path)
        docs   = loader.load()

        logger.info("Loaded %d document(s) from %s", len(docs), file_path)
        return docs

    def load_directory(self, directory: str) -> list[Document]:
        """
        Load all supported files from a directory (non-recursive).

        Args:
            directory: Path to the folder containing documents.

        Returns:
            Combined list of Document objects from all loaded files.
        """
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"Directory not found: {directory}")

        all_docs: list[Document] = []

        for filename in os.listdir(directory):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in self.SUPPORTED_LOADERS:
                logger.debug("Skipping unsupported file: %s", filename)
                continue

            file_path = os.path.join(directory, filename)
            try:
                docs = self.load(file_path)
                all_docs.extend(docs)
            except Exception as exc:
                # Log and continue — one bad file shouldn't stop everything
                logger.error("Failed to load %s: %s", file_path, exc)

        logger.info(
            "Directory load complete: %d documents from %s",
            len(all_docs), directory,
        )
        return all_docs
