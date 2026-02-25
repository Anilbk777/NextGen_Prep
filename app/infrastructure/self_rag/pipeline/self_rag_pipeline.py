"""
pipeline/self_rag_pipeline.py

Master orchestrator for the Self-RAG pipeline.
Implements all 6 steps as private methods and drives the full
revision loop with a configurable maximum number of attempts.

Pipeline steps
--------------
Step 1  _step1_retrieval_decision()   → should the pipeline retrieve?
Step 2  _step2_retrieve_and_filter()  → fetch docs + ISREL relevance filter
Step 3  _step3_generate_candidates()  → one answer per relevant document
Step 4  _step4_detect_hallucinations()→ ISSUP hallucination filter
Step 5  _step5_score_and_rank()       → ISUSE scoring + weighted final score
Step 6  _step6_revision_or_finalise() → decide: accept answer or rewrite query

Revision loop
-------------
Steps 2–6 run in a while-loop capped at MAX_REVISION_TRIES.
Rewrite triggers:
    a) 0 relevant docs after Step 2
    b) 0 grounded candidates after Step 4
    c) best_score < MIN_USEFULNESS_SCORE after Step 5

Loop exit:
    a) best_score >= MIN_USEFULNESS_SCORE  → succeeded=True
    b) revision_attempt >= MAX_REVISION_TRIES → succeeded=False, best-effort answer
"""

from __future__ import annotations

import logging
import time

from ..generation.generator     import Generator
from ..generation.query_rewriter import QueryRewriter
from ..reflection.critic         import Critic
from ..reflection.tokens         import (
    ISUPPToken, ISUSEToken, RetrieveToken,
    ISSUP_SCORES, normalise_isuse,
)
from ..retrieval.retriever       import Retriever
from .. import config
from .state                      import RAGState

logger = logging.getLogger(__name__)


class SelfRAGPipeline:
    """
    Wires all Self-RAG components together and runs the full pipeline.

    Args:
        critic:   Critic instance (4 reflection chains)
        generator: Generator instance (context + no-context chains)
        rewriter: QueryRewriter instance
        retriever: Retriever instance (wraps LocalVectorStore)

    Usage
    -----
    result = pipeline.run("What is the capital of France?")
    print(result.final_answer)
    print(result.succeeded)       # True if answer met quality threshold
    print(result.revision_attempt)# How many rewrites were needed
    """

    def __init__(
        self,
        critic:    Critic,
        generator: Generator,
        rewriter:  QueryRewriter,
        retriever: Retriever,
    ) -> None:
        self._critic    = critic
        self._generator = generator
        self._rewriter  = rewriter
        self._retriever = retriever

    # ===================================================================
    # Public entry point
    # ===================================================================

    def run(self, query: str) -> RAGState:
        """
        Execute the full Self-RAG pipeline for a single query.

        Args:
            query: The user's question.

        Returns:
            A RAGState object containing the final answer, quality score,
            and all intermediate state for debugging/auditing.
        """
        if not query.strip():
            raise ValueError("query must not be empty.")

        logger.info("=== Self-RAG pipeline started | query='%s...' ===", query[:70])
        overall_start = time.perf_counter()

        # Initialise state — carries all data through the pipeline
        state = RAGState(
            original_query=query,
            current_query=query,
        )

        # ---------------------------------------------------------------
        # Step 1 — Retrieval decision
        # ---------------------------------------------------------------
        state = self._step1_retrieval_decision(state)

        if not state.retrieval_used:
            # LLM can answer from knowledge alone — skip straight to generation
            state.final_answer = self._generator.generate_without_context(state.current_query)
            state.best_score   = config.MIN_USEFULNESS_SCORE  # treat as met
            state.succeeded    = True
            logger.info(
                "=== Pipeline complete (no retrieval) | %.2fs ===",
                time.perf_counter() - overall_start,
            )
            return state

        # ---------------------------------------------------------------
        # Steps 2–6 — Retrieve → Generate → Reflect → Revise loop
        # ---------------------------------------------------------------
        while state.revision_attempt < config.MAX_REVISION_TRIES:
            state.revision_attempt += 1
            logger.info("--- Revision attempt %d/%d ---", state.revision_attempt, config.MAX_REVISION_TRIES)

            state = self._step2_retrieve_and_filter(state)

            if not state.relevant_docs:
                logger.info("No relevant docs found — rewriting query.")
                state = self._rewrite_query(state)
                continue  # back to Step 2 with fresh query

            state = self._step3_generate_candidates(state)

            if not state.candidate_answers:
                logger.warning("No candidates generated — rewriting query.")
                state = self._rewrite_query(state)
                continue

            state = self._step4_detect_hallucinations(state)

            if not state.candidate_answers:
                logger.info("All candidates hallucinated — rewriting query.")
                state = self._rewrite_query(state)
                continue

            state = self._step5_score_and_rank(state)

            if state.best_score >= config.MIN_USEFULNESS_SCORE:
                # Quality threshold met — we're done
                state.succeeded = True
                logger.info(
                    "Quality threshold met (score=%.2f >= %.2f). Finalising.",
                    state.best_score, config.MIN_USEFULNESS_SCORE,
                )
                break
            else:
                logger.info(
                    "Score %.2f below threshold %.2f — rewriting query.",
                    state.best_score, config.MIN_USEFULNESS_SCORE,
                )
                state = self._rewrite_query(state)

        # If we exhausted retries without meeting threshold, we still return
        # the best answer we found (best-effort).
        if not state.succeeded:
            logger.warning(
                "Max revision attempts (%d) reached. Returning best-effort answer (score=%.2f).",
                config.MAX_REVISION_TRIES, state.best_score,
            )
            # If we reached max retries and still have no answer, provide a helpful fallback
            if not state.final_answer:
                state.final_answer = config.DEFAULT_FALLBACK_MESSAGE

        elapsed = time.perf_counter() - overall_start
        logger.info(
            "=== Self-RAG pipeline complete | succeeded=%s | score=%.2f | %.2fs ===",
            state.succeeded, state.best_score, elapsed,
        )
        return state

    # ===================================================================
    # Private step methods
    # ===================================================================

    def _step1_retrieval_decision(self, state: RAGState) -> RAGState:
        """Step 1: Decide whether external retrieval is needed for this query."""
        token = self._critic.should_retrieve(state.current_query)
        state.retrieval_used = (token == RetrieveToken.YES)

        logger.info(
            "Step 1 | Retrieval decision: %s (retrieval_used=%s)",
            token.value, state.retrieval_used,
        )
        return state

    def _step2_retrieve_and_filter(self, state: RAGState) -> RAGState:
        """
        Step 2: Retrieve top-k documents from the vector store, then filter
        each one through the ISREL critic to keep only relevant passages.
        """
        # Retrieve raw documents
        state.retrieved_docs = self._retriever.retrieve(state.current_query)

        if not state.retrieved_docs:
            logger.warning("Step 2 | No documents retrieved.")
            state.relevant_docs = []
            return state

        # Filter by ISREL relevance
        relevant = []
        for doc in state.retrieved_docs:
            token = self._critic.is_relevant(state.current_query, doc.page_content)
            if token.value == "relevant":
                relevant.append(doc)

        state.relevant_docs = relevant
        logger.info(
            "Step 2 | %d/%d documents passed ISREL filter.",
            len(relevant), len(state.retrieved_docs),
        )
        return state

    def _step3_generate_candidates(self, state: RAGState) -> RAGState:
        """
        Step 3: Generate one candidate answer from each relevant document.
        Each candidate is grounded in a single passage.
        """
        state.candidate_answers = self._generator.generate_from_documents(
            state.current_query, state.relevant_docs
        )
        logger.info("Step 3 | %d candidate answers generated.", len(state.candidate_answers))
        return state

    def _step4_detect_hallucinations(self, state: RAGState) -> RAGState:
        """
        Step 4: Check each (candidate, source_doc) pair with ISSUP critic.
        - FULLY / PARTIALLY supported → keep
        - NOT supported → discard (hallucinated)
        Keeps candidates and their support scores in sync.
        """
        grounded_candidates: list[str] = []
        grounded_scores:     list[str] = []   # ISUPPToken values

        for answer, doc in zip(state.candidate_answers, state.relevant_docs):
            token = self._critic.is_supported(answer, doc.page_content)

            if token == ISUPPToken.NOT:
                logger.debug("Step 4 | Hallucinated candidate discarded.")
                continue

            grounded_candidates.append(answer)
            grounded_scores.append(token.value)

        state.candidate_answers = grounded_candidates
        state.support_scores    = grounded_scores

        logger.info(
            "Step 4 | %d/%d candidates passed hallucination check.",
            len(grounded_candidates), len(state.relevant_docs),
        )
        return state

    def _step5_score_and_rank(self, state: RAGState) -> RAGState:
        """
        Step 5: Score each grounded candidate with ISUSE (1–5), compute a
        weighted final score, then pick the best candidate as the final answer.

        Final score formula (from config):
            final_score = (ISSUP_WEIGHT * issup_score) + (ISUSE_WEIGHT * norm_isuse)
        """
        final_scores:     list[float] = []
        usefulness_scores: list[int]  = []

        for answer, issup_value in zip(state.candidate_answers, state.support_scores):
            # ISUSE score (1–5)
            isuse_score = self._critic.is_useful(state.current_query, answer)
            usefulness_scores.append(isuse_score)

            # ISSUP numeric weight
            issup_token = ISUPPToken(issup_value)
            issup_score = ISSUP_SCORES[issup_token]

            # Weighted combined score
            combined = (
                (config.ISSUP_WEIGHT * issup_score) +
                (config.ISUSE_WEIGHT * normalise_isuse(isuse_score))
            )
            final_scores.append(combined)

        state.usefulness_scores = usefulness_scores
        state.final_scores      = final_scores

        # Pick the best candidate
        if final_scores:
            best_idx          = final_scores.index(max(final_scores))
            state.final_answer = state.candidate_answers[best_idx]
            state.best_score   = final_scores[best_idx]
            logger.info(
                "Step 5 | Best candidate: idx=%d, score=%.2f, isuse=%d",
                best_idx, state.best_score, usefulness_scores[best_idx],
            )
        else:
            state.best_score = 0.0

        return state

    def _rewrite_query(self, state: RAGState) -> RAGState:
        """
        Helper: rewrite the current query using the QueryRewriter and reset
        per-attempt state fields so the next iteration starts fresh.
        """
        state.current_query = self._rewriter.rewrite(
            query=state.current_query,
            failed_answer=state.final_answer,
            attempt=state.revision_attempt,
        )
        # Reset per-attempt state
        state.retrieved_docs    = []
        state.relevant_docs     = []
        state.candidate_answers = []
        state.support_scores    = []
        state.usefulness_scores = []
        state.final_scores      = []
        return state
