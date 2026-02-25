"""
self_rag_main.py

Entry point for the Self-RAG pipeline.
Assembles all components, runs optional indexing, and executes queries.

Environment
-----------
Requires GROQ_API_KEY in .env or environment for Groq LLM models.

How to use
----------
# Index documents (first run only — or whenever documents change)
from app.infrastructure.self_rag.self_rag_main import build_pipeline, index_documents

index_documents("./path/to/your/docs")

# Run a query
pipeline = build_pipeline()
result   = pipeline.run("What topics are covered in Chapter 3?")
print(result.final_answer)

# Or run a quick one-shot query:
from app.infrastructure.self_rag.self_rag_main import ask
print(ask("What is photosynthesis?"))
"""

from __future__ import annotations

import logging
import os

from langchain_groq import ChatGroq

from . import config
from .generation.generator     import Generator
from .generation.query_rewriter import QueryRewriter
from .pipeline.self_rag_pipeline import SelfRAGPipeline
from .pipeline.state             import RAGState
from .reflection.critic          import Critic
from .retrieval.retriever        import Retriever
from .vectorstore.embedder       import Embedder
from .vectorstore.indexer        import Indexer
from .vectorstore.store          import LocalVectorStore
from .ingestion.text_splitter    import TextSplitter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Factory — assemble all components
# ---------------------------------------------------------------------------

def _create_llm(model_name: str | None = None) -> ChatGroq:
    """
    Create a Groq LLM client for a specific model.
    GROQ_API_KEY must be set in the environment (or .env file).
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file or export it in the terminal."
        )

    model = model_name or config.LLM_MODEL
    try: 
        return ChatGroq(
            model=model,
            api_key=api_key,
            temperature=0,      # deterministic — better for factual Q&A
            max_tokens=1024,
            max_retries=5,
        )
    except Exception as e:
        logger.error("Failed to create LLM for model %s: %s", model, e)
        raise Exception(f"Chat model {model} is not working")


def _create_vector_store() -> LocalVectorStore:
    """Create the embedder and vector store."""
    embedder = Embedder(model_name=config.EMBEDDING_MODEL)
    store    = LocalVectorStore(
        embedding_function=embedder.get(),
        persist_directory=config.VECTOR_STORE_PATH,
    )
    return store


def build_pipeline(load_existing: bool = True) -> SelfRAGPipeline:
    """
    Assemble and return a fully configured SelfRAGPipeline.
    """
    # Create specific LLMs for each component
    critic_retrieval_llm = _create_llm(config.CRITIC_RETRIEVAL_MODEL)
    critic_relevance_llm = _create_llm(config.CRITIC_RELEVANCE_MODEL)
    critic_support_llm   = _create_llm(config.CRITIC_SUPPORT_MODEL)
    critic_useful_llm    = _create_llm(config.CRITIC_USEFUL_MODEL)
    
    gen_llm = _create_llm(config.GENERATOR_MODEL)
    rw_llm  = _create_llm(config.REWRITER_MODEL)

    store = _create_vector_store()

    if load_existing:
        if store.collection_exists():
            store.load_existing()
        else:
            logger.warning(
                "No vector store found at '%s'. "
                "Run index_documents() first to create one.",
                config.VECTOR_STORE_PATH,
            )

    pipeline = SelfRAGPipeline(
        critic    = Critic(
            retrieval_llm = critic_retrieval_llm,
            relevance_llm = critic_relevance_llm,
            support_llm   = critic_support_llm,
            useful_llm    = critic_useful_llm
        ),
        generator = Generator(gen_llm),
        rewriter  = QueryRewriter(rw_llm),
        retriever = Retriever(store, top_k=config.TOP_K_RETRIEVAL),
    )
    return pipeline


def get_indexer() -> Indexer:
    """
    Create and return a configured Indexer.
    Use this to index new documents into the vector store.
    """
    store    = _create_vector_store()
    splitter = TextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    return Indexer(text_splitter=splitter, vector_store=store)


# ---------------------------------------------------------------------------
# Convenience functions (one-liners for scripts and management commands)
# ---------------------------------------------------------------------------

def index_documents(path: str | None = None) -> None:
    """
    Index all documents at the given file path or directory.

    Args:
        path: Path to a single file or a directory of files.
              Defaults to config.UPLOADS_DIR
              (C:\\Users\\Dell\\Desktop\\NextGen_Prep\\backend\\uploads).
    """
    import os as _os

    target = path or config.UPLOADS_DIR
    logger.info("Indexing documents from: %s", target)

    indexer = get_indexer()
    if _os.path.isdir(target):
        indexer.index_directory(target)
    else:
        indexer.index(target)


def index_uploads() -> None:
    """
    Convenience shortcut: index all files in the uploads folder.

    Equivalent to index_documents() with no arguments.
    The uploads path is defined in config.UPLOADS_DIR.
    """
    index_documents()   # uses config.UPLOADS_DIR by default


def ask(query: str) -> str:
    """
    One-shot convenience function: build pipeline, run query, return answer.

    Useful for scripts and quick testing.

    Args:
        query: The user's question.

    Returns:
        The final answer string.
    """
    pipeline = build_pipeline()
    result   = pipeline.run(query)
    return result.final_answer


# ---------------------------------------------------------------------------
# CLI — run directly: python -m app.infrastructure.self_rag.self_rag_main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  Index uploads folder  : python self_rag_main.py index")
        print(f"  Index specific path   : python self_rag_main.py index <path>")
        print( "  Ask a question        : python self_rag_main.py ask '<your question>'")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "index":
        target = sys.argv[2] if len(sys.argv) >= 3 else None
        index_documents(target)   # defaults to uploads/ if no path given
        print(f"Indexing complete: {target or config.UPLOADS_DIR}")

    elif command == "ask" and len(sys.argv) >= 3:
        question = " ".join(sys.argv[2:])
        answer   = ask(question)
        print("\n=== Answer ===")
        print(answer)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
