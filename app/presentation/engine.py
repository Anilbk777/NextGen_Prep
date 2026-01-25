from functools import lru_cache
from ...core.adaptive_engine import AdaptiveLearningEngine


@lru_cache
def get_adaptive_engine() -> AdaptiveLearningEngine:
    """
    Singleton adaptive engine instance.
    Safe because DB state is externalized.
    """
    return AdaptiveLearningEngine()
