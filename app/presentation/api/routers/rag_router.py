from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from fastapi.responses import StreamingResponse
from app.presentation.schemas.rag_schema import RAGQuery, RAGResponse, ChatHistoryResponse
from app.infrastructure.self_rag.self_rag_main import build_pipeline
from app.presentation.dependencies import get_current_user, get_db
from app.infrastructure.repositories.chat_history_repository import ChatHistoryRepository
from sqlalchemy.orm import Session
import logging
import json

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


@router.post("/stream")
async def stream_chat(
    query_data: RAGQuery,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Streaming endpoint for Self-RAG. 
    Returns Server-Sent Events (SSE) and persists completion.
    """
    if _pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Self-RAG pipeline is not initialized.",
        )

    async def event_generator():
        full_response_parts = []
        try:
            async for event in _pipeline.astream(query_data.query):
                # Buffer tokens for persistence
                try:
                    data = json.loads(event)
                    if data.get("type") == "token":
                        full_response_parts.append(data.get("content", ""))
                except:
                    pass

                # Proper SSE format: data: <payload>\n\n
                yield f"data: {event}\n\n"
            
            # Persistent storage after successful stream
            if full_response_parts:
                try:
                    repo = ChatHistoryRepository(db)
                    repo.add(
                        user_id=current_user["user_id"],
                        user_query=query_data.query,
                        content="".join(full_response_parts)
                    )
                except Exception as save_err:
                    logger.error(f"Failed to persist chat history: {save_err}")

            # End of stream event
            yield "event: end\ndata: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Error in streaming: {e}", exc_info=True)
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get("/conversations", response_model=List[ChatHistoryResponse])
def get_chat_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve chat history for the current authenticated user.
    """
    try:
        repo = ChatHistoryRepository(db)
        history = repo.get_by_user_id(current_user["user_id"])
        
        # Convert created_at to string for schema compatibility
        return [
            ChatHistoryResponse(
                id=h.id,
                user_query=h.user_query,
                content=h.content,
                created_at=h.created_at.isoformat() if h.created_at else ""
            ) for h in history
        ]
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve chat history.")
