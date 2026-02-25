"""

RAGState dataclass — the single shared context object that flows
through every step of the Self-RAG pipeline.

Design principles
-----------------
- One object carries all state. No step reads from or writes to
  anything outside RAGState. This makes the pipeline fully testable
  and debuggable — you can inspect or replay any step by examining
  the state snapshot before and after.

- All fields have safe defaults so the pipeline can construct an
  initial state with just a query string.

- The state is mutable — each pipeline step receives it, mutates
  specific fields, and returns it. Steps never replace the entire
  object, only update the fields they own.

- CriticDecision objects are stored for full audit trail —
  the pipeline can explain every decision it made.
"""

from dataclasses import dataclass, field
from langchain_core.documents import Document

@dataclass
class RAGState:
    # Input
    original_query:     str = ""
    current_query:      str = ""          # updated on each rewrite

    # Retrieval
    retrieved_docs:     list[Document] = field(default_factory=list)
    relevant_docs:      list[Document] = field(default_factory=list)

    # Generation
    candidate_answers:  list[str]      = field(default_factory=list)

    # Scoring
    support_scores:     list[str]      = field(default_factory=list)   # ISUPPToken values
    usefulness_scores:  list[int]      = field(default_factory=list)
    final_scores:       list[float]    = field(default_factory=list)   # combined score

    # Output
    final_answer:       str  = ""
    best_score:         float = 0.0

    # Control
    retrieval_used:     bool = True
    revision_attempt:   int  = 0
    succeeded:          bool = False