from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from presentation.schemas.topic_schema import TopicCreate, TopicOut
from infrastructure.db.models.topic_model import Topic
from presentation.dependencies import get_db, admin_required
from infrastructure.repositories.topic_repo_impl import (
    create_topic,
    get_topics_by_subject,
    get_all_topics,
    get_topic_by_id,
    update_topic,
    delete_topic,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["Topics"])
# ==================== STATS ====================
# count the number of topics  
@router.get("/count", response_model=int)
def count_topics(db: Session = Depends(get_db)):
    return db.query(Topic).count()


# ==================== CREATE ====================
@router.post("", response_model=TopicOut)
def add_topic(
    topic: TopicCreate,
    subject_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Create a new topic for organizing MCQs"""
    try:
        logger.info(
            f"Admin {admin['user_id']} creating topic: {topic.name} for subject_id: {subject_id}"
        )
        result = create_topic(db, subject_id, topic)
        return result
    except ValueError as e:
        logger.warning(f"Topic creation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Topic creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==================== READ ====================
@router.get("", response_model=list[TopicOut])
def list_topics(
    subject_id: int | None = Query(None),
    db: Session = Depends(get_db)
):
    """Get all topics, optionally filtered by subject_id"""
    try:
        if subject_id:
            logger.info(
                f" fetching topics for subject_id: {subject_id}"
            )
            topics = get_topics_by_subject(db, subject_id)
        else:
            logger.info(f" fetching all topics")
            topics = get_all_topics(db)
        return topics
    except Exception as e:
        logger.error(f"Error fetching topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/{topic_id}", response_model=TopicOut)
def get_topic(
    topic_id: int, db: Session = Depends(get_db)
):
    """Get a specific topic by ID"""
    try:
        logger.info(f" fetching topic {topic_id}")
        topic = get_topic_by_id(db, topic_id)
        return topic
    except ValueError as e:
        logger.warning(f"Topic not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching topic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==================== UPDATE ====================
@router.patch("/{topic_id}", response_model=TopicOut)
def modify_topic(
    topic_id: int,
    topic: TopicCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Update a topic"""
    try:
        logger.info(f"Admin {admin['user_id']} updating topic {topic_id}")
        result = update_topic(db, topic_id, topic)
        return result
    except ValueError as e:
        logger.warning(f"Topic update error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating topic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==================== DELETE ====================
@router.delete("/{topic_id}")
def remove_topic(
    topic_id: int, db: Session = Depends(get_db), admin: dict = Depends(admin_required)
):
    """Delete a topic (will fail if MCQs are associated with it)"""
    try:
        logger.info(f"Admin {admin['user_id']} deleting topic {topic_id}")
        result = delete_topic(db, topic_id)
        return result
    except ValueError as e:
        logger.warning(f"Topic deletion error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting topic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


