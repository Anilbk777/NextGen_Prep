from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from infrastructure.db.models.subject_model import PracticeSubject
from presentation.schemas.subject_schema import PracticeSubjectCreate,PracticeSubjectOut
import logging

logger = logging.getLogger(__name__)


def create_practice_subject(
    db: Session, subject_data: PracticeSubjectCreate
) -> PracticeSubjectOut:
    """Create a new practice subject"""
    try:
        # Check if subject already exists
        existing = (
            db.query(PracticeSubject)
            .filter(PracticeSubject.name == subject_data.name)
            .first()
        )

        if existing:
            logger.warning(
                f"Attempt to create duplicate practice subject: {subject_data.name}"
            )
            raise ValueError(f"Practice subject '{subject_data.name}' already exists")

        subject = PracticeSubject(
            name=subject_data.name, description=subject_data.description
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
        logger.info(f"Created practice subject: {subject.name} (ID: {subject.id})")
        return PracticeSubjectOut.from_orm(subject)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error creating practice subject: {e}")
        raise ValueError(f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating practice subject: {e}", exc_info=True)
        raise


def get_all_practice_subjects(db: Session):
    """Get all practice subjects"""
    try:
        subjects = db.query(PracticeSubject).order_by(PracticeSubject.name).all()
        logger.info(f"Retrieved {len(subjects)} practice subjects")
        return [PracticeSubjectOut.from_orm(subject) for subject in subjects]
    except Exception as e:
        logger.error(f"Error fetching practice subjects: {e}", exc_info=True)
        raise


def _get_subject_model(db: Session, subject_id: int) -> PracticeSubject:
    """Internal helper to get the SQLAlchemy model instance"""
    subject = (
        db.query(PracticeSubject).filter(PracticeSubject.id == subject_id).first()
    )
    if not subject:
        logger.warning(f"Practice subject with id {subject_id} not found")
        raise ValueError(f"Practice subject with id {subject_id} not found")
    return subject


def get_practice_subject_by_id(db: Session, subject_id: int):
    """Get a specific practice subject by ID"""
    try:
        subject = _get_subject_model(db, subject_id)
        logger.info(f"Retrieved practice subject: {subject.name} (ID: {subject_id})")
        return PracticeSubjectOut.from_attribute(subject) if hasattr(PracticeSubjectOut, "from_attribute") else PracticeSubjectOut.from_orm(subject)
    except ValueError:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching practice subject {subject_id}: {e}", exc_info=True
        )
        raise


def update_practice_subject(db: Session, subject_id: int, subject_data: PracticeSubjectCreate):
    """Update a practice subject"""
    try:
        subject = _get_subject_model(db, subject_id)

        # Check if new name conflicts with existing subject
        if subject_data.name != subject.name:
            existing = (
                db.query(PracticeSubject)
                .filter(PracticeSubject.name == subject_data.name)
                .first()
            )
            if existing:
                logger.warning(
                    f"Cannot update practice subject {subject_id}: name '{subject_data.name}' already exists"
                )
                raise ValueError(
                    f"Practice subject name '{subject_data.name}' already exists"
                )

        subject.name = subject_data.name
        subject.description = subject_data.description
        db.commit()
        db.refresh(subject)
        logger.info(f"Updated practice subject: {subject.name} (ID: {subject_id})")
        return PracticeSubjectOut.from_attribute(subject) if hasattr(PracticeSubjectOut, "from_attribute") else PracticeSubjectOut.from_orm(subject)

    except IntegrityError as e:
        db.rollback()
        logger.error(
            f"Database integrity error updating practice subject {subject_id}: {e}"
        )
        raise ValueError(f"Database error: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error updating practice subject {subject_id}: {e}",
            exc_info=True,
        )
        raise


def delete_practice_subject(db: Session, subject_id: int):
    """Delete a practice subject"""
    try:
        
        subject = _get_subject_model(db, subject_id)
        subject_name = subject.name
        db.delete(subject)
        db.commit()
        logger.info(f"Deleted practice subject: {subject_name} (ID: {subject_id})")
        return {"message": f"Practice subject '{subject_name}' deleted successfully"}

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Cannot delete practice subject {subject_id}: {e}")
        raise ValueError(
            f"Cannot delete practice subject: it has associated topics, MCQs, or notes"
        )
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error deleting practice subject {subject_id}: {e}",
            exc_info=True,
        )
        raise
