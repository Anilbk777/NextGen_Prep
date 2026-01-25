from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.presentation.schemas.template_schema import TemplateCreate, TemplateOut
from app.infrastructure.repositories.template_repository import TemplateRepository
from app.presentation.dependencies import get_db, admin_required

router = APIRouter(prefix="/templates", tags=["Admin Templates"])

@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required)
):
    """
    Admin: Add a new template for a concept.
    """
    repo = TemplateRepository(db)
    return repo.create_template(template)

@router.get("", response_model=List[TemplateOut])
def list_templates(
    topic_id: Optional[int] = Query(None),
    concept_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    repo = TemplateRepository(db)
    return repo.get_all(topic_id=topic_id, concept_id=concept_id)

@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    repo = TemplateRepository(db)
    db_template = repo.get_by_id(template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_template

@router.patch("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    template: TemplateCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required)
):
    repo = TemplateRepository(db)
    db_template = repo.update_template(template_id, template)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_template

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required)
):
    repo = TemplateRepository(db)
    if not repo.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return None
