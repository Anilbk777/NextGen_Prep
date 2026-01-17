from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from infrastructure.db.models.topic_model import Topic
from presentation.schemas.topic_schema import TopicCreate
import logging

logger = logging.getLogger(__name__)

def create_topic(db: Session, topic_data: TopicCreate) -> Topic:
    """Create a new topic"""
    try:
        # Check if topic already exists for this subject
        existing = db.query(Topic).filter(
            Topic.name == topic_data.name,
            Topic.subject_id == topic_data.subject_id
        ).first()
        
        if existing:
            logger.warning(f"Attempt to create duplicate topic: {topic_data.name} for subject_id: {topic_data.subject_id}")
            raise ValueError(f"Topic '{topic_data.name}' already exists for this subject")
        
        topic = Topic(
            name=topic_data.name,
            subject_id=topic_data.subject_id
        )
        db.add(topic)
        db.commit()
        db.refresh(topic)
        logger.info(f"Created topic: {topic.name} (ID: {topic.id}) for subject_id: {topic.subject_id}")
        return topic
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error creating topic: {e}")
        raise ValueError(f"Invalid subject_id or database error: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating topic: {e}", exc_info=True)
        raise

def get_topics_by_subject(db: Session, subject_id: int):
    """Get all topics for a specific subject"""
    try:
        topics = db.query(Topic).filter(Topic.subject_id == subject_id).all()
        logger.info(f"Retrieved {len(topics)} topics for subject_id: {subject_id}")
        return topics
    except Exception as e:
        logger.error(f"Error fetching topics for subject_id {subject_id}: {e}", exc_info=True)
        raise

def get_all_topics(db: Session):
    """Get all topics"""
    try:
        topics = db.query(Topic).all()
        logger.info(f"Retrieved {len(topics)} topics")
        return topics
    except Exception as e:
        logger.error(f"Error fetching all topics: {e}", exc_info=True)
        raise

def get_topic_by_id(db: Session, topic_id: int):
    """Get a specific topic by ID"""
    try:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            logger.warning(f"Topic with id {topic_id} not found")
            raise ValueError(f"Topic with id {topic_id} not found")
        logger.info(f"Retrieved topic: {topic.name} (ID: {topic_id})")
        return topic
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error fetching topic {topic_id}: {e}", exc_info=True)
        raise

def update_topic(db: Session, topic_id: int, topic_data: TopicCreate) -> Topic:
    """Update a topic"""
    try:
        topic = get_topic_by_id(db, topic_id)
        
        # Check if new name conflicts with existing topic for the same subject
        if topic_data.name != topic.name or topic_data.subject_id != topic.subject_id:
            existing = db.query(Topic).filter(
                Topic.name == topic_data.name,
                Topic.subject_id == topic_data.subject_id,
                Topic.id != topic_id  # Exclude current topic
            ).first()
            
            if existing:
                logger.warning(f"Cannot update topic {topic_id}: name '{topic_data.name}' already exists for subject_id {topic_data.subject_id}")
                raise ValueError(f"Topic name '{topic_data.name}' already exists for this subject")
        
        topic.name = topic_data.name
        topic.subject_id = topic_data.subject_id
        db.commit()
        db.refresh(topic)
        logger.info(f"Updated topic: {topic.name} (ID: {topic_id})")
        return topic
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error updating topic {topic_id}: {e}")
        raise ValueError(f"Database error: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating topic {topic_id}: {e}", exc_info=True)
        raise

def delete_topic(db: Session, topic_id: int):
    """Delete a topic"""
    try:
        topic = get_topic_by_id(db, topic_id)
        topic_name = topic.name
        db.delete(topic)
        db.commit()
        logger.info(f"Deleted topic: {topic_name} (ID: {topic_id})")
        return {"message": f"Topic '{topic_name}' deleted successfully"}
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Cannot delete topic {topic_id}: {e}")
        raise ValueError(f"Cannot delete topic: it has associated MCQs")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting topic {topic_id}: {e}", exc_info=True)
        raise
