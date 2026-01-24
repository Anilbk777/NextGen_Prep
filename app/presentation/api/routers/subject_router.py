from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from infrastructure.db.models.subject_model import PracticeSubject
from presentation.schemas.subject_schema import PracticeSubjectCreate, PracticeSubjectOut
from presentation.dependencies import get_db, admin_required
from infrastructure.repositories.subject_repo_impl import (
    create_practice_subject,
    get_all_practice_subjects,
    get_practice_subject_by_id,
    update_practice_subject,
    delete_practice_subject,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subjects", tags=["Subjects"])


# count the number of subjects  
@router.get("/count", response_model=int)
def count_subjects(db: Session = Depends(get_db)):
    return db.query(PracticeSubject).count()


@router.post("", response_model=PracticeSubjectOut)
def add_subject(
    subject: PracticeSubjectCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        return create_practice_subject(db, subject)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[PracticeSubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return get_all_practice_subjects(db)


@router.get("/{subject_id}", response_model=PracticeSubjectOut)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_practice_subject_by_id(db, subject_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{subject_id}", response_model=PracticeSubjectOut)
def modify_subject(
    subject_id: int,
    subject: PracticeSubjectCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        return update_practice_subject(db, subject_id, subject)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{subject_id}")
def remove_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        return delete_practice_subject(db, subject_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


