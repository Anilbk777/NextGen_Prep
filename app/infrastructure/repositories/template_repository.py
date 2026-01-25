from typing import List, Optional
from sqlalchemy.orm import Session
from ..db.models import Template

class TemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_template(self, template_data) -> Template:
        db_template = Template(
            concept_id=template_data.concept_id,
            topic_id=template_data.topic_id,
            learning_objective=template_data.learning_objective,
            target_difficulty=template_data.target_difficulty,
            question_style=template_data.question_style,
            answer_format=template_data.answer_format,
            config_metadata=template_data.config_metadata
        )
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template

    def get_by_id(self, template_id: int) -> Optional[Template]:
        return self.db.query(Template).filter(Template.template_id == template_id).first()

    def get_all(self, topic_id: Optional[int] = None, concept_id: Optional[int] = None) -> List[Template]:
        query = self.db.query(Template)
        if topic_id:
            query = query.filter(Template.topic_id == topic_id)
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
        Returns templates for bandit consumption, filtered by topic.
        """
        return self.db.query(Template).filter(Template.topic_id == topic_id).all()
