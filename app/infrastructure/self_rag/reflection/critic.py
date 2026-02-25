"""
reflection/critic.py

Production-grade critic model for the Self-RAG reflection layer.
Implements all four Self-RAG reflection tokens as individual LCEL chains.

Each method:
    1. Validates inputs
    2. Invokes a LangChain LCEL chain (prompt | llm | StrOutputParser)
    3. Parses the raw LLM output into a typed token via tokens.py
    4. Logs the decision with timing
    5. Returns a typed token — never a raw string

Pipeline positions:
    Step 1  → should_retrieve()  → RetrieveToken
    Step 2  → is_relevant()      → ISRELToken
    Step 4  → is_supported()     → ISUPPToken   (hallucination detection)
    Step 6  → is_useful()        → int (1–5)
"""

from __future__ import annotations

import logging
import time

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from ..generation.prompt_templates import (
    RETRIEVAL_DECISION_PROMPT,
    RELEVANCE_CHECK_PROMPT,
    HALLUCINATION_CHECK_PROMPT,
    USEFULNESS_SCORE_PROMPT,
)
from .tokens import ISRELToken, ISUPPToken, ISUSEToken, RetrieveToken

logger = logging.getLogger(__name__)


class Critic:
    """
    Wraps four LangChain LCEL chains for the Self-RAG reflection tokens.

    Each chain follows the same pattern:
        prompt | llm | StrOutputParser

    The raw LLM output (a string) is then parsed into the correct enum token.
    If the LLM returns an unexpected value, a safe fallback is used to avoid
    crashing the pipeline.
    """

    def __init__(
        self,
        retrieval_llm: BaseChatModel,
        relevance_llm: BaseChatModel,
        support_llm:   BaseChatModel,
        useful_llm:    BaseChatModel,
    ) -> None:
        self._parser = StrOutputParser()

        # Build four LCEL chains with their respective LLMs
        self._should_retrieve_chain = RETRIEVAL_DECISION_PROMPT | retrieval_llm | self._parser
        self._is_relevant_chain     = RELEVANCE_CHECK_PROMPT    | relevance_llm | self._parser
        self._is_supported_chain    = HALLUCINATION_CHECK_PROMPT | support_llm   | self._parser
        self._is_useful_chain       = USEFULNESS_SCORE_PROMPT   | useful_llm    | self._parser

    # ------------------------------------------------------------------
    # Step 1 — Should we retrieve external documents?
    # ------------------------------------------------------------------

    def should_retrieve(self, query: str) -> RetrieveToken:
        """
        Decide whether the query needs external retrieval.

        Returns:
            RetrieveToken.YES → go fetch documents
            RetrieveToken.NO  → answer directly from LLM knowledge
        """
        if not query.strip():
            raise ValueError("query must not be empty.")

        start  = time.perf_counter()
        raw    = self._should_retrieve_chain.invoke({"query": query})
        elapsed = time.perf_counter() - start

        # LLM should return "yes" or "no" — normalise and parse
        token_str = raw.strip().lower()
        token     = RetrieveToken.YES if token_str == "yes" else RetrieveToken.NO

        logger.debug(
            "should_retrieve | query='%s...' | token=%s | %.3fs",
            query[:60], token.value, elapsed,
        )
        return token

    # ------------------------------------------------------------------
    # Step 2 — Is this document relevant to the query?
    # ------------------------------------------------------------------

    def is_relevant(self, query: str, document: str) -> ISRELToken:
        """
        Decide whether a retrieved document passage is relevant to the query.

        Returns:
            ISRELToken.RELEVANT   → use this document for generation
            ISRELToken.IRRELEVANT → discard this document
        """
        if not query.strip() or not document.strip():
            raise ValueError("query and document must not be empty.")

        start  = time.perf_counter()
        raw    = self._is_relevant_chain.invoke({"query": query, "document": document})
        elapsed = time.perf_counter() - start

        token_str = raw.strip().lower()
        # Default to IRRELEVANT if the LLM returns something unexpected
        token = (
            ISRELToken.RELEVANT
            if token_str == ISRELToken.RELEVANT.value
            else ISRELToken.IRRELEVANT
        )

        logger.debug(
            "is_relevant | token=%s | %.3fs", token.value, elapsed
        )
        return token

    # ------------------------------------------------------------------
    # Step 4 — Is the answer grounded in the document? (hallucination check)
    # ------------------------------------------------------------------

    def is_supported(self, answer: str, document: str) -> ISUPPToken:
        """
        Determine how well the generated answer is supported by the source document.

        Returns:
            ISUPPToken.FULLY     → fully grounded, no hallucination
            ISUPPToken.PARTIALLY → some claims ungrounded
            ISUPPToken.NOT       → hallucinated — discard this answer
        """
        if not answer.strip() or not document.strip():
            raise ValueError("answer and document must not be empty.")

        start  = time.perf_counter()
        raw    = self._is_supported_chain.invoke({"answer": answer, "document": document})
        elapsed = time.perf_counter() - start

        token_str = raw.strip().lower()

        # Map LLM output to the correct token, defaulting to NOT_SUPPORTED on unknown
        if token_str == ISUPPToken.FULLY.value:
            token = ISUPPToken.FULLY
        elif token_str == ISUPPToken.PARTIALLY.value:
            token = ISUPPToken.PARTIALLY
        else:
            token = ISUPPToken.NOT

        logger.debug(
            "is_supported | token=%s | %.3fs", token.value, elapsed
        )
        return token

    # ------------------------------------------------------------------
    # Step 6 — How useful is this answer?
    # ------------------------------------------------------------------

    def is_useful(self, query: str, answer: str) -> int:
        """
        Score how well the answer addresses the query on a 1–5 scale.

        Returns:
            Integer score 1 (poor) → 5 (excellent).
            Returns 1 as a safe fallback if the LLM output is unparsable.
        """
        if not query.strip() or not answer.strip():
            raise ValueError("query and answer must not be empty.")

        start  = time.perf_counter()
        raw    = self._is_useful_chain.invoke({"query": query, "answer": answer})
        elapsed = time.perf_counter() - start

        # Parse the integer score; fallback to 1 if unparsable
        try:
            score = int(raw.strip())
            score = max(1, min(5, score))  # clamp to valid range
        except (ValueError, TypeError):
            logger.warning("is_useful: unparsable LLM output '%s' — defaulting to 1", raw)
            score = 1

        logger.debug(
            "is_useful | score=%d | %.3fs", score, elapsed
        )
        return score