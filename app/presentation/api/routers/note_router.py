from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.presentation.dependencies import get_db, admin_required
from app.infrastructure.repositories.note_repo import (
    create_note,
    get_notes_by_topic,
    get_note_by_id,
    update_note,
    delete_note,
    get_all_notes,
)
from app.infrastructure.db.models.notes import Note
from app.presentation.schemas.notes import NoteResponse,NoteUpdate
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["Notes"])

# count the numbers of notes
@router.get("/count", response_model=int)
def count_notes(db: Session = Depends(get_db)):
    return db.query(Note).count()


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
BASE_URL = "http://127.0.0.1:8000/uploads"  # base URL for frontend

# get all notes 

@router.get("/all", response_model=List[NoteResponse])
def get_all(db: Session = Depends(get_db)):
    try:
        return get_all_notes(db)
    except Exception as e:
        logger.error(f"Failed to retrieve notes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve notes: {str(e)}",
        )

@router.post("/", response_model=NoteResponse)
def upload_note(
    topic_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    file_url = f"{BASE_URL}/{file.filename}"  # URL to serve to frontend

    try:
        # Write file to local disk
        with open(file_location, "wb") as f:
            f.write(file.file.read())

        # Save to DB
        note = create_note(
            db=db,
            topic_id=topic_id,
            title=title,
            file_path=file_url,  # store URL, not local path
            file_size=os.path.getsize(file_location),
            mime_type=file.content_type,
        )

    except Exception as e:
        logger.error(
            f"Failed to upload note '{title}' for topic {topic_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload note: {str(e)}",
        )
    else:
        logger.info(f"Note '{title}' uploaded successfully for topic {topic_id}")
        return note


@router.get(
    "/topic/{topic_id}",
    response_model=List[NoteResponse],
    summary="Get all notes for a topic",
)
def get_notes_of_topic(topic_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all notes associated with a given topic.
    """
    try:
        notes = get_notes_by_topic(db=db, topic_id=topic_id)
        return notes
    except Exception as e:
        logger.error(
            f"Failed to retrieve notes for topic {topic_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve notes: {str(e)}",
        )


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
)
def fetch_note(
    note_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_note_by_id(db, note_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{note_id}",
    response_model=NoteResponse,
)
def patch_note(
    note_id: int,
    note_data: NoteUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_note(db, note_id, note_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_200_OK,
)
def remove_note(
    note_id: int,
    db: Session = Depends(get_db),
):
    try:
        return delete_note(db, note_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


