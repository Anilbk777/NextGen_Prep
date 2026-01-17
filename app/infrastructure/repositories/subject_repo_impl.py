from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from infrastructure.db.models.subject_model import Subject
from presentation.schemas.subject_schema import SubjectCreate
import logging

logger = logging.getLogger(__name__)

def create_subject(db: Session, subject_data: SubjectCreate) -> Subject:
    """Create a new subject"""
    try:
        # Check if subject already exists
        existing = db.query(Subject).filter(Subject.name == subject_data.name).first()
        
        if existing:
            logger.warning(f"Attempt to create duplicate subject: {subject_data.name}")
            raise ValueError(f"Subject '{subject_data.name}' already exists")
        
        subject = Subject(
            name=subject_data.name,
            description=subject_data.description
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
        logger.info(f"Created subject: {subject.name} (ID: {subject.id})")
        return subject
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error creating subject: {e}")
        raise ValueError(f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating subject: {e}", exc_info=True)
        raise

def get_all_subjects(db: Session):
    """Get all subjects"""
    try:
        subjects = db.query(Subject).order_by(Subject.name).all()
        logger.info(f"Retrieved {len(subjects)} subjects")
        return subjects
    except Exception as e:
        logger.error(f"Error fetching subjects: {e}", exc_info=True)
        raise

def get_subject_by_id(db: Session, subject_id: int):
    """Get a specific subject by ID"""
    try:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            logger.warning(f"Subject with id {subject_id} not found")
            raise ValueError(f"Subject with id {subject_id} not found")
        logger.info(f"Retrieved subject: {subject.name} (ID: {subject_id})")
        return subject
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error fetching subject {subject_id}: {e}", exc_info=True)
        raise

def update_subject(db: Session, subject_id: int, subject_data: SubjectCreate):
    """Update a subject"""
    try:
        subject = get_subject_by_id(db, subject_id)
        
        # Check if new name conflicts with existing subject
        if subject_data.name != subject.name:
            existing = db.query(Subject).filter(Subject.name == subject_data.name).first()
            if existing:
                logger.warning(f"Cannot update subject {subject_id}: name '{subject_data.name}' already exists")
                raise ValueError(f"Subject name '{subject_data.name}' already exists")
        
        subject.name = subject_data.name
        subject.description = subject_data.description
        db.commit()
        db.refresh(subject)
        logger.info(f"Updated subject: {subject.name} (ID: {subject_id})")
        return subject
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error updating subject {subject_id}: {e}")
        raise ValueError(f"Database error: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating subject {subject_id}: {e}", exc_info=True)
        raise

def delete_subject(db: Session, subject_id: int):
    """Delete a subject"""
    try:
        subject = get_subject_by_id(db, subject_id)
        subject_name = subject.name
        db.delete(subject)
        db.commit()
        logger.info(f"Deleted subject: {subject_name} (ID: {subject_id})")
        return {"message": f"Subject '{subject_name}' deleted successfully"}
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Cannot delete subject {subject_id}: {e}")
        raise ValueError(f"Cannot delete subject: it has associated topics, MCQs, or mock tests")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting subject {subject_id}: {e}", exc_info=True)
        raise
