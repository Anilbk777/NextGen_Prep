"""
reflection/tokens.py

Typed enumerations for the four Self-RAG reflection tokens.
These tokens are the core decision signals that drive every
conditional branch in the Self-RAG pipeline.

Token overview
--------------
RetrieveToken   : Should the pipeline retrieve external documents?
ISRELToken      : Is a retrieved document relevant to the query?
ISUPPToken      : Is the generated answer supported by the document?
ISUSEToken      : How useful is the answer to the original query? (1–5)

Each token is a str-based Enum so it can be:
    - Compared directly to LLM string output  → "relevant" == ISRELToken.RELEVANT
    - Serialised to JSON / logged without extra conversion
    - Used as a TypedDict value in RAGState

Scoring helpers
---------------
ISSUP_SCORES    : ISUPPToken  → float weight for final candidate scoring
ISUSE_NORMALISE : Normalise ISUSEToken int (1–5) to 0.0–1.0 range
"""

from __future__ import annotations

from enum import Enum
from typing import Final


# ---------------------------------------------------------------------------
# Token 1 — Retrieval Decision
# ---------------------------------------------------------------------------

class RetrieveToken(str, Enum):
    """
    Controls whether the pipeline fetches documents from the vector store.

    YES → proceed to retrieve_documents
    NO  → skip to generate_without_retrieval
    """
    YES = "yes"
    NO  = "no"


# ---------------------------------------------------------------------------
# Token 2 — Document Relevance (ISREL)
# ---------------------------------------------------------------------------

class ISRELToken(str, Enum):
    """
    Indicates whether a retrieved document is relevant to the query.

    RELEVANT   → use this document for generation
    IRRELEVANT → discard this document, do not generate from it
    """
    RELEVANT   = "relevant"
    IRRELEVANT = "irrelevant"


# ---------------------------------------------------------------------------
# Token 3 — Answer Support / Hallucination Detection (ISSUP)
# ---------------------------------------------------------------------------

class ISUPPToken(str, Enum):
    """
    Indicates how well a generated answer is grounded in its source document.

    FULLY     → answer is completely supported — keep and score highly
    PARTIALLY → answer is partially supported — keep but penalise in scoring
    NOT       → answer is not supported (hallucinated) — discard immediately

    This token is the primary hallucination detection signal in Step 4.
    """
    FULLY     = "fully_supported"
    PARTIALLY = "partially_supported"
    NOT       = "not_supported"


# ---------------------------------------------------------------------------
# Token 4 — Answer Usefulness (ISUSE)
# ---------------------------------------------------------------------------

class ISUSEToken(int, Enum):
    """
    Rates how well the generated answer addresses the original query.
    Integer scale 1 (poor) to 5 (excellent).

    Used in Step 6 to:
        1. Select the best candidate answer from multiple options
        2. Decide whether to trigger the revision loop or finalise

    Combined with ISSUP score to produce a weighted final_score:
        final_score = (ISSUP_WEIGHT * issup_score) + (ISUSE_WEIGHT * normalised_isuse)
    """
    POOR      = 1
    WEAK      = 2
    AVERAGE   = 3
    GOOD      = 4
    EXCELLENT = 5


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

# Maps each ISUPPToken to a numeric weight used in final candidate scoring.
# fully_supported = full score | partially = half | not_supported = discard (0)
ISSUP_SCORES: Final[dict[ISUPPToken, float]] = {
    ISUPPToken.FULLY:     1.0,
    ISUPPToken.PARTIALLY: 0.5,
    ISUPPToken.NOT:       0.0,
}


def normalise_isuse(score: int) -> float:
    """
    Normalise an ISUSEToken integer (1–5) to the 0.0–1.0 range.

    Formula:  (score - 1) / 4
        1 → 0.00   (worst)
        3 → 0.50   (average)
        5 → 1.00   (best)
    """
    return (max(1, min(5, score)) - 1) / 4.0