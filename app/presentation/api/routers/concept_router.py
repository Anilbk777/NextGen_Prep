from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.presentation.schemas.concept_schema import ConceptCreate, ConceptOut
from app.infrastructure.repositories.concept_repository import ConceptRepository
from app.presentation.dependencies import get_db, admin_required

router = APIRouter(prefix="/concepts", tags=["Admin Concepts"])

@router.post("", response_model=ConceptOut, status_code=status.HTTP_201_CREATED)
def create_concept(
    concept: ConceptCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required)
):
    """
    Admin: Add a new concept to a topic.
    """
    repo = ConceptRepository(db)
    return repo.create_concept(concept)

@router.get("", response_model=List[ConceptOut])
def list_concepts(
    topic_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List concepts, optionally filtered by topic.
    """
    repo = ConceptRepository(db)
    if topic_id:
        return repo.get_by_topic(topic_id)
    # Could add get_all if needed, for now filtering is essential
    return []

@router.get("/{concept_id}", response_model=ConceptOut)
def get_concept(concept_id: int, db: Session = Depends(get_db)):
    repo = ConceptRepository(db)
    db_concept = repo.get_by_id(concept_id)
    if not db_concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return db_concept

@router.patch("/{concept_id}", response_model=ConceptOut)
def update_concept(
    concept_id: int,
    concept: ConceptCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required)
):
    repo = ConceptRepository(db)
    db_concept = repo.update_concept(concept_id, concept)
    if not db_concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return db_concept

@router.delete("/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_concept(
    concept_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required)
):
    repo = ConceptRepository(db)
    if not repo.delete_concept(concept_id):
        raise HTTPException(status_code=404, detail="Concept not found")
    return None
