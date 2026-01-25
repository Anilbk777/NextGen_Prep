from typing import List, Optional
from sqlalchemy.orm import Session
from ..db.models import Question, Template, Concept

class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_candidate_templates(self, topic_id: int) -> List[Template]:
        """
        Fetch templates filtered by topic.
        """
        return (
            self.db.query(Template)
            .filter(Template.topic_id == topic_id)
            .all()
        )

    def get_cached_question(self, template_id: int) -> Optional[Question]:
        return (
            self.db.query(Question)
            .filter(Question.template_id == template_id)
            .first()
        )

    def get_by_id(self, question_id: int) -> Optional[Question]:
        return (
            self.db.query(Question)
            .filter(Question.question_id == question_id)
            .first()
        )

    def get_concept(self, concept_id: int) -> Optional[Concept]:
        return (
            self.db.query(Concept)
            .filter(Concept.concept_id == concept_id)
            .first()
        )
    
    def save_question(self, question: Question) -> Question:
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question
