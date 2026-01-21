from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from infrastructure.db.models.notes import Note
from infrastructure.db.models.topic_model import Topic
from presentation.schemas.notes import NoteUpdate
import logging
from typing import List

logger = logging.getLogger(__name__)


def create_note(
    db: Session,
    topic_id: int,
    title: str,
    file_path: str,
    file_size: int,
    mime_type: str,
) -> Note:
    """Create a new note for a given topic."""
    # Verify topic exists
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        logger.warning(f"Note creation failed: Topic {topic_id} not found")
        raise ValueError(f"Topic with ID {topic_id} does not exist.")

    # Optional: basic input validation
    if not title or file_size <= 0:
        raise ValueError("Invalid title or file size")

    existing = (
        db.query(Note).filter(Note.title == title, Note.topic_id == topic_id).first()
    )
    if existing:
        logger.warning(f"Duplicate note '{title}' for topic_id {topic_id}")
        raise ValueError(f"Note '{title}' already exists for topic {topic_id}")

    note = Note(
        topic_id=topic_id,
        title=title,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
    )

    try:
        db.add(note)
        db.commit()
        db.refresh(note)
        logger.info(
            f"Created note '{note.title}' (ID: {note.id}) for topic_id {note.topic_id}"
        )
        return note

    except IntegrityError as e:
        db.rollback()
        logger.error(f"DB integrity error creating note: {e}")
        raise ValueError(f"Invalid topic_id or duplicate note: {str(e)}")

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating note: {e}", exc_info=True)
        raise


def get_notes_by_topic(db: Session, topic_id: int) -> List[Note]:
    try:
        notes: List[Note] = db.query(Note).filter(Note.topic_id == topic_id).all()
        logger.info(f"Retrived {len(notes)} notes for topic_id={topic_id}")
        return notes
    except Exception as e:
        logger.error(
            f"Error fetching notes for topic_id = {topic_id}: {e}", exc_info=True
        )
        raise


def get_note_by_id(db: Session, note_id: int) -> Note:
    """Get a specific note by ID"""
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            logger.warning(f"Note with id {note_id} not found")
            raise ValueError(f"Note with id {note_id} not found")

        logger.info(f"Retrieved note: {note.title} (ID: {note_id})")
        return note
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error fetching note {note_id}: {e}", exc_info=True)
        raise


def get_all_notes(db: Session) -> List[Note]:
    """Get all notes"""
    try:
        notes = db.query(Note).all()
        logger.info(f"Retrieved {len(notes)} notes")
        return notes
    except Exception as e:
        logger.error(f"Error fetching all notes: {e}", exc_info=True)
        raise


def update_note(
    db: Session,
    note_id: int,
    note_data: NoteUpdate,
) -> Note:
    """Update a note"""
    try:
        note = get_note_by_id(db, note_id)

        # Prevent duplicate title within same topic
        if note_data.title and note_data.title != note.title:
            existing = (
                db.query(Note)
                .filter(
                    Note.title == note_data.title,
                    Note.topic_id == note.topic_id,
                    Note.id != note_id,
                )
                .first()
            )

            if existing:
                logger.warning(f"Cannot update note {note_id}: title already exists")
                raise ValueError(
                    f"Note '{note_data.title}' already exists for this topic"
                )

        for field, value in note_data.model_dump(exclude_unset=True).items():
            setattr(note, field, value)

        db.commit()
        db.refresh(note)

        logger.info(f"Updated note '{note.title}' (ID={note_id})")
        return note

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error updating note {note_id}: {e}")
        raise ValueError("Database constraint error")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error updating note {note_id}: {e}",
            exc_info=True,
        )
        raise


def delete_note(db: Session, note_id: int):
    """Delete a note"""
    try:
        note = get_note_by_id(db, note_id)
        note_title = note.title

        db.delete(note)
        db.commit()

        logger.info(f"Deleted note '{note_title}' (ID={note_id})")
        return {"message": f"Note '{note_title}' deleted successfully"}

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Cannot delete note {note_id}: {e}")
        raise ValueError("Cannot delete note due to database constraints")
    except ValueError:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error deleting note {note_id}: {e}",
            exc_info=True,
        )
        raise
