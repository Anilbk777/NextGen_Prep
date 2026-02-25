"""
generation/query_rewriter.py

Production-grade query rewriter for the Self-RAG revision loop.
Rewrites a failed query to retrieve better documents on the next attempt.

Pipeline position:
    Step 5/6 → [QueryRewriter] → back to Step 2 (retrieve_and_filter)

The rewriter is called when:
    a) No relevant documents were found (0 ISREL passes)
    b) All candidate answers were hallucinated (0 ISSUP passes)
    c) Best answer scored below MIN_USEFULNESS_SCORE

Each rewrite attempt uses a progressively more aggressive strategy
(specified in the prompt): add specificity → decompose → rephrase →
broaden → simplify. The attempt number is passed to the prompt so
the LLM can apply the right strategy at each stage.
"""

from __future__ import annotations

import logging
import time

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from .prompt_templates import QUERY_REWRITE_PROMPT
from .. import config

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    Rewrites a failed query using a single LCEL chain:
        QUERY_REWRITE_PROMPT | llm | StrOutputParser

    The rewrite strategy escalates with each attempt number.
    Attempt numbers and strategies are defined in QUERY_REWRITE_PROMPT.

    Args:
        llm: Any LangChain chat model.
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = QUERY_REWRITE_PROMPT | llm | StrOutputParser()

    def rewrite(
        self,
        query:         str,
        failed_answer: str,
        attempt:       int,
    ) -> str:
        """
        Rewrite a query that failed to produce a good answer.

        Args:
            query:         The original (or previously rewritten) query.
            failed_answer: The best answer produced so far (insufficient).
            attempt:       Current revision attempt number (1-indexed).

        Returns:
            A rewritten query string.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")

        start = time.perf_counter()

        rewritten = self._chain.invoke({
            "query":         query,
            "failed_answer": failed_answer or "(no answer was generated)",
            "attempt":       attempt,
            "max_attempts":  config.MAX_REVISION_TRIES,
        })

        elapsed = time.perf_counter() - start

        rewritten = rewritten.strip()
        logger.info(
            "Query rewritten [attempt %d/%d] | '%s...' → '%s...' | %.3fs",
            attempt, config.MAX_REVISION_TRIES,
            query[:50], rewritten[:50], elapsed,
        )
        return rewritten