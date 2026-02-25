import os

# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
CHUNK_SIZE    = 600
CHUNK_OVERLAP = 150

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K_RETRIEVAL = 5

# ---------------------------------------------------------------------------
# Self-RAG loop control
# ---------------------------------------------------------------------------
MAX_REVISION_TRIES   = 5
# MIN_USEFULNESS_SCORE = 3   # answers scoring below this (1–5 scale) trigger a rewrite
MIN_USEFULNESS_SCORE = 0.8 # normalized threshold (0.0–1.0). 0.8 requires high support and usefulness.
DEFAULT_FALLBACK_MESSAGE = "No data found. Please try a different query or be more specific."
RATE_LIMIT_ERROR_MESSAGE = "API rate limit exceeded. Too many retries, please try again in a few minutes."

# ---------------------------------------------------------------------------
# Scoring weights  (must sum to 1.0)
# ---------------------------------------------------------------------------
ISSUP_WEIGHT = 0.6   # hallucination-support score weight
ISUSE_WEIGHT = 0.4   # usefulness score weight

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
# Models
LLM_MODEL = "llama-3.3-70b-versatile" # Default fallback

# Reflection (Critic) Models
CRITIC_RETRIEVAL_MODEL = "llama-3.3-70b-versatile"
CRITIC_RELEVANCE_MODEL = "llama-3.3-70b-versatile"
CRITIC_SUPPORT_MODEL   = "llama-3.3-70b-versatile"
CRITIC_USEFUL_MODEL    = "llama-3.3-70b-versatile"

# Generation & Rewriting Models
GENERATOR_MODEL = "llama-3.3-70b-versatile"
REWRITER_MODEL  = "llama-3.3-70b-versatile"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"          # runs fully locally via sentence-transformers

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Folder where uploaded documents are stored
UPLOADS_DIR = os.path.join(
    os.path.dirname(__file__),          # .../self_rag/
    "..", "..", "..",                  # up to backend/
    "uploads",
)
UPLOADS_DIR = os.path.normpath(UPLOADS_DIR)   # clean the path

# ChromaDB persistence directory (created automatically on first index)
VECTOR_STORE_PATH = os.path.join(
    os.path.dirname(__file__),
    "vectorstore", "local_db",
)
VECTOR_STORE_PATH = os.path.normpath(VECTOR_STORE_PATH)