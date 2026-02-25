"""
self_rag — Self-RAG pipeline package.

Import individual submodules directly for lightweight use:

    from app.infrastructure.self_rag.ingestion.document_loader import DocumentLoader
    from app.infrastructure.self_rag.vectorstore.store import LocalVectorStore

To build the full query pipeline (requires GROQ_API_KEY):

    from app.infrastructure.self_rag.self_rag_main import build_pipeline, ask
"""
# Intentionally empty — no eager imports.
# Importing self_rag_main here would pull in langchain_groq + the full LLM stack
# at server startup, which is unnecessarily heavy and slow.
# Use direct submodule imports instead (see docstring above).
