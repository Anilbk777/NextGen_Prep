from typing import List, Optional
from sqlalchemy.orm import Session
from ..db.models import Template

class TemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_template(self, template_data) -> Template:
        db_template = Template(
            concept_id=template_data.concept_id,
            intent=template_data.intent,
            learning_objective=template_data.learning_objective,
            target_difficulty=template_data.target_difficulty,
            question_style=template_data.question_style,
            correct_reasoning=template_data.correct_reasoning,
            misconception_patterns=template_data.misconception_patterns,
            answer_format=template_data.answer_format
        )
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    def get_by_id(self, template_id: int) -> Optional[Template]:
        return self.db.query(Template).filter(Template.template_id == template_id).first()

    def get_all(self, concept_id: Optional[int] = None) -> List[Template]:
        query = self.db.query(Template)
        if concept_id:
            query = query.filter(Template.concept_id == concept_id)
        return query.all()

    def update_template(self, template_id: int, template_data) -> Optional[Template]:
        db_template = self.get_by_id(template_id)
        if not db_template:
            return None
        
        for key, value in template_data.dict(exclude_unset=True).items():
            setattr(db_template, key, value)
        
        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    def delete_template(self, template_id: int) -> bool:
        db_template = self.get_by_id(template_id)
        if not db_template:
            return False
        self.db.delete(db_template)
        self.db.commit()
        return True

    def get_candidate_templates(self, topic_id: int) -> List[Template]:
        """
        Returns templates for a topic by joining with concepts.
        """
        from ..db.models import Concept
        return (
            self.db.query(Template)
            .join(Concept, Template.concept_id == Concept.concept_id)
            .filter(Concept.topic_id == topic_id)
            .all()
        )
