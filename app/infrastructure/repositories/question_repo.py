import logging
from sqlalchemy import func
from ..db.models import PracticeMCQ, OptionModel
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_random_by_difficulty(self, topic_id: int, difficulty: str, limit: int):
        """Fetch random MCQs by difficulty for a given topic."""
        try:
            return (
                self.db.query(PracticeMCQ)
                .filter(
                    PracticeMCQ.topic_id == topic_id,
                    PracticeMCQ.difficulty == difficulty
                )
                .order_by(func.random())
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching random questions for topic {topic_id}, difficulty {difficulty}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error fetching questions")

    def get_option(self, option_id: int) -> OptionModel:
        """Fetch a single option by ID."""
        return self.db.query(OptionModel).filter(OptionModel.id == option_id).first()