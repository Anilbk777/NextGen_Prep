"""
generation/query_rewriter.py

Production-grade query rewriter for the Self-RAG revision loop.
Rewrites a failed query to retrieve better documents on the next attempt.
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

    async def arewrite(
        self,
        query:         str,
        failed_answer: str,
        attempt:       int,
    ) -> str:
        """
        Rewrite a failed query asynchronously.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")

        rewritten = await self._chain.ainvoke({
            "query":         query,
            "failed_answer": failed_answer or "(no answer was generated)",
            "attempt":       attempt,
            "max_attempts":  config.MAX_REVISION_TRIES,
        })
        return rewritten.strip()