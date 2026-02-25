# presentation/routes/recommendation.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.presentation.dependencies import get_db, get_current_user

from app.infrastructure.repositories.topic_recommed_repo import TopicRecommendRepository
from app.infrastructure.services.topic_recommendation_service import (
    TopicRecommendationService,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recommend Topics"])


@router.get("/recommendations")
def get_recommendations(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    user_id = current_user["user_id"]

    try: 
        repository = TopicRecommendRepository(db)
        service = TopicRecommendationService(repository)

    except Exception as e:
        logger.error(f"Failed to provide recommendation =: {e}")
        raise HTTPException("Failed to recommend Topics ")

    return service.recommend_topics(user_id)
