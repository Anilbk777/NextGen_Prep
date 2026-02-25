# schemas/recommendation_schema.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class TopicRecommendation:
    topic_id: int
    topic_name: str
    topic_mastery: float
    coverage: float
    weakness_score: float
    reason: Optional[str] = None
