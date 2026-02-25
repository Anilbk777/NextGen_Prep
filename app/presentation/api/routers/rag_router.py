from fastapi import APIRouter, HTTPException, Depends
from app.presentation.schemas.rag_schema import RAGQuery, RAGResponse
from app.infrastructure.self_rag.self_rag_main import build_pipeline
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["Self-RAG"])

# Initialize the pipeline lazily or at module level
# Reusing the same pipeline instance to benefit from the cached embedder
try:
    _pipeline = build_pipeline()
except Exception as e:
    logger.error(f"Failed to initialize Self-RAG pipeline: {e}")
    _pipeline = None


@router.post("/ask", response_model=RAGResponse)
def ask_question(query_data: RAGQuery):
    """
    Ask a question using the Self-RAG pipeline.
    The pipeline will decide if retrieval is needed, search documents,
    reflect on accuracy, and rewrite the query if necessary.
    """
    if _pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Self-RAG pipeline is not initialized. Check server logs and GROQ_API_KEY.",
        )

    try:
        result = _pipeline.run(query_data.query)

        return RAGResponse(
            final_answer=result.final_answer,
            succeeded=result.succeeded,
            revision_attempt=result.revision_attempt,
            best_score=result.best_score,
            retrieval_used=result.retrieval_used,
            current_query=result.current_query,
        )
    except Exception as e:
        logger.error(f"Error during RAG process: {e}", exc_info=True)
        
        # Check for Groq Rate Limit (429) specifically
        err_msg = str(e).lower()
        if any(keyword in err_msg for keyword in ["429", "rate limit", "too many requests", "rate_limit_exceeded"]):
             from app.infrastructure.self_rag import config
             # Return a 200 OK with the error message in the body so it shows in chat
             return RAGResponse(
                final_answer=config.RATE_LIMIT_ERROR_MESSAGE,
                succeeded=False,
                revision_attempt=0,
                best_score=0.0,
                retrieval_used=True,
                current_query=query_data.query
            )

        raise HTTPException(
            status_code=500,
            detail="Chat is not working, please try again in few minutes.",
        )
