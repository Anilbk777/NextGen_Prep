"""
generation/generator.py

Production-grade answer generator for the Self-RAG pipeline.
Wraps two LangChain LCEL chains — one for context-grounded generation
(Step 3) and one for direct generation when no retrieval is needed
(Step 1 branch).

Pipeline positions:
    Step 1 branch → generate_without_context()   (retrieval not needed)
    Step 3        → generate_with_context()       (one answer per relevant doc)
    Step 3 batch  → generate_from_documents()     (all relevant docs at once)
"""

from __future__ import annotations

import logging
import time

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from .prompt_templates import (
    ANSWER_WITH_CONTEXT_PROMPT,
    ANSWER_WITHOUT_CONTEXT_PROMPT,
)

from groq import RateLimitError

logger = logging.getLogger(__name__)


class Generator:
    """
    Generates answers using two LCEL chains:

    Chain A — with_context:
        ANSWER_WITH_CONTEXT_PROMPT | llm | StrOutputParser
        Used in Step 3: one answer is generated per relevant document.

    Chain B — without_context:
        ANSWER_WITHOUT_CONTEXT_PROMPT | llm | StrOutputParser
        Used when Step 1 decides no retrieval is needed.

    Args:
        llm: Any LangChain chat model (Groq, OpenAI, Ollama, etc.)
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._parser = StrOutputParser()

        self._with_context_chain    = ANSWER_WITH_CONTEXT_PROMPT    | llm | self._parser
        self._without_context_chain = ANSWER_WITHOUT_CONTEXT_PROMPT | llm | self._parser

    # ------------------------------------------------------------------
    # Step 3 — Generate one answer from one document
    # ------------------------------------------------------------------

    def generate_with_context(self, query: str, context: str) -> str:
        """
        Generate an answer grounded in a specific context passage.

        Args:
            query:   The user's original question.
            context: The document passage to use as context.

        Returns:
            A factually grounded answer string.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")
        if not context.strip():
            raise ValueError("context must not be empty.")

        start  = time.perf_counter()
        answer = self._with_context_chain.invoke({"query": query, "context": context})
        elapsed = time.perf_counter() - start

        logger.debug(
            "generate_with_context | query='%s...' | %.3fs",
            query[:60], elapsed,
        )
        return answer.strip()

    def generate_from_documents(
        self, query: str, documents: list[Document]
    ) -> list[str]:
        """
        Generate one candidate answer per relevant document.

        This is the main Step 3 call in the pipeline — it produces a pool
        of candidate answers that Step 4 (ISSUP) and Step 6 (ISUSE) then
        evaluate and rank.

        Args:
            query:     The user's original question.
            documents: List of relevant documents (already ISREL-filtered).

        Returns:
            List of candidate answer strings (one per document).
        """
        if not documents:
            return []

        candidates: list[str] = []

        for i, doc in enumerate(documents):
            try:
                answer = self.generate_with_context(query, doc.page_content)
                candidates.append(answer)
                logger.debug("Candidate %d/%d generated.", i + 1, len(documents))
            except RateLimitError:
                # Re-raise rate limit errors so the router can catch them
                raise
            except Exception as exc:
                logger.error("Failed to generate from document %d: %s", i, exc)

        logger.info(
            "Generated %d candidate answers from %d documents.",
            len(candidates), len(documents),
        )
        return candidates

    # ------------------------------------------------------------------
    # Step 3 — Generate one answer from one document (Streaming)
    # ------------------------------------------------------------------

    async def astream_with_context(self, query: str, context: str):
        """
        Async generator for an answer grounded in a specific context passage.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")
        if not context.strip():
            raise ValueError("context must not be empty.")

        async for chunk in self._with_context_chain.astream({"query": query, "context": context}):
            yield chunk

    def generate_without_context(self, query: str) -> str:
        """
        Generate an answer directly from the LLM's internal knowledge.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")

        return self._without_context_chain.invoke({"query": query}).strip()

    async def astream_without_context(self, query: str):
        """
        Async generator for an answer based solely on LLM knowledge.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")

        async for chunk in self._without_context_chain.astream({"query": query}):
            yield chunk
