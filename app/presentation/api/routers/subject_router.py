from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from presentation.schemas.subject_schema import SubjectCreate, SubjectOut
from presentation.dependencies import get_db, admin_required
from infrastructure.repositories.subject_repo_impl import (
    create_subject,
    get_all_subjects,
    get_subject_by_id,
    update_subject,
    delete_subject,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.post("", response_model=SubjectOut)
def add_subject(
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        return create_subject(db, subject)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db), admin: dict = Depends(admin_required)):
    return get_all_subjects(db)


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        return get_subject_by_id(db, subject_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{subject_id}", response_model=SubjectOut)
def modify_subject(
    subject_id: int,
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        return update_subject(db, subject_id, subject)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{subject_id}")
def remove_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        return delete_subject(db, subject_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
