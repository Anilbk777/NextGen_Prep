from sqlalchemy.orm import Session
from typing import List, Optional
from app.infrastructure.db.models import Concept

class ConceptRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_concept(self, concept_data) -> Concept:
        db_concept = Concept(
            topic_id=concept_data.topic_id,
            name=concept_data.name,
            description=concept_data.description,
            prerequisites=concept_data.prerequisites,
            common_misconceptions=concept_data.common_misconceptions,
            difficulty_level=concept_data.difficulty_level
        )
        self.db.add(db_concept)
        self.db.commit()
        self.db.refresh(db_concept)
        return db_concept

    def get_by_id(self, concept_id: int) -> Optional[Concept]:
        return self.db.query(Concept).filter(Concept.concept_id == concept_id).first()

    def get_by_topic(self, topic_id: int) -> List[Concept]:
        return self.db.query(Concept).filter(Concept.topic_id == topic_id).all()

    def update_concept(self, concept_id: int, concept_data) -> Optional[Concept]:
        db_concept = self.get_by_id(concept_id)
        if not db_concept:
            return None
        
        for key, value in concept_data.dict(exclude_unset=True).items():
            setattr(db_concept, key, value)
        
        self.db.commit()
        self.db.refresh(db_concept)
        return db_concept

    def delete_concept(self, concept_id: int) -> bool:
        db_concept = self.get_by_id(concept_id)
        if not db_concept:
            return False
        self.db.delete(db_concept)
        self.db.commit()
        return True
