from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from infrastructure.db.models.topic_model import Topic
from infrastructure.db.models.subject_model import PracticeSubject
from presentation.schemas.topic_schema import TopicCreate,TopicOut
import logging

logger = logging.getLogger(__name__)

def create_topic(db: Session, subject_id: int, topic_data: TopicCreate) -> TopicOut:
    """Create a new topic"""
    try:
        # Verify subject exists
        subject = db.query(PracticeSubject).filter(PracticeSubject.id == subject_id).first()
        if not subject:
            logger.warning(f"Topic creation failed: Subject {subject_id} not found")
            raise ValueError(f"Subject with ID {subject_id} does not exist.")

        # Check if topic already exists for this subject
        existing = db.query(Topic).filter(
            Topic.name == topic_data.name,
            Topic.subject_id == subject_id
        ).first()
        
        if existing:
            logger.warning(f"Attempt to create duplicate topic: {topic_data.name} for subject_id: {subject_id}")
            raise ValueError(f"Topic '{topic_data.name}' already exists for this subject")
        
        topic = Topic(
            name=topic_data.name,
            subject_id=subject_id
        )
        db.add(topic)
        db.commit()
        db.refresh(topic)
        logger.info(f"Created topic: {topic.name} (ID: {topic.id}) for subject_id: {subject_id}")
        return TopicOut.from_orm(topic)
    
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
        return [TopicOut.from_orm(topic) for topic in topics]
    except Exception as e:
        logger.error(f"Error fetching topics for subject_id {subject_id}: {e}", exc_info=True)
        raise

def get_all_topics(db: Session):
    """Get all topics"""
    try:
        topics = db.query(Topic).all()
        logger.info(f"Retrieved {len(topics)} topics")
        return [TopicOut.from_orm(topic) for topic in topics]
    except Exception as e:
        logger.error(f"Error fetching all topics: {e}", exc_info=True)
        raise

def _get_topic_model(db: Session, topic_id: int) -> Topic:
    """Internal helper to get the SQLAlchemy model instance"""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        logger.warning(f"Topic with id {topic_id} not found")
        raise ValueError(f"Topic with id {topic_id} not found")
    return topic


def get_topic_by_id(db: Session, topic_id: int):
    """Get a specific topic by ID"""
    try:
        topic = _get_topic_model(db, topic_id)
        logger.info(f"Retrieved topic: {topic.name} (ID: {topic_id})")
        return TopicOut.from_attribute(topic) if hasattr(TopicOut, "from_attribute") else TopicOut.from_orm(topic)
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error fetching topic {topic_id}: {e}", exc_info=True)
        raise


def update_topic(db: Session, topic_id: int, topic_data: TopicCreate) -> TopicOut:
    """Update a topic"""
    try:
        topic = _get_topic_model(db, topic_id)

        # Check if new name conflicts with existing topic for the same subject
        if topic_data.name != topic.name and topic_data.subject_id != topic.subject_id:
            existing = db.query(Topic).filter(
                Topic.name == topic_data.name,
                Topic.subject_id == topic_data.subject_id,
                Topic.id != topic_id  # Exclude current topic
            ).first()

            if existing:
                logger.warning(f"Cannot update topic {topic_id}: name '{topic_data.name}' already exists for subject_id {topic_data.subject_id}")
                raise ValueError(f"Topic name '{topic_data.name}' already exists for this subject")

        temp =  db.query(PracticeSubject).filter(PracticeSubject.id== topic_data.subject_id).first() 
        if not temp:
            logger.error("The subject id,you are trying to modify doesnot exist")
            raise ValueError(f"Modifying process failed because subject id {topic_data.subject_id} does not exist")
        
        topic.name = topic_data.name
        topic.subject_id = topic_data.subject_id
        
        db.commit()
        db.refresh(topic)
        logger.info(f"Updated topic: {topic.name} (ID: {topic_id})")
        return TopicOut.from_attribute(topic) if hasattr(TopicOut, "from_attribute") else TopicOut.from_orm(topic)

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
        topic = _get_topic_model(db, topic_id)
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
