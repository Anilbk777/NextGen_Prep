from typing import List, Optional
import logging
from sqlalchemy.orm import Session
from ..db.models import Question, Template, Concept, UserResponse

logger = logging.getLogger(__name__)


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_candidate_templates(self, topic_id: int) -> List[Template]:
        """
        Fetch templates filtered by topic (via Concept).
        """
        logger.info(f"Fetching candidate templates for topic_id={topic_id}")
        templates = (
            self.db.query(Template)
            .join(Concept, Template.concept_id == Concept.concept_id)
            .filter(Concept.topic_id == topic_id)
            .all()
        )
        logger.info(f"Found {len(templates)} candidate templates for topic_id={topic_id}")
        return templates

    def get_cached_question(self, template_id: int) -> Optional[Question]:
        logger.debug(f"Looking for cached question for template_id={template_id}")
        question = (
            self.db.query(Question)
            .filter(Question.template_id == template_id)
            .first()
        )
        if question:
            logger.info(f"Cache hit: Found question_id={question.question_id} for template_id={template_id}")
        else:
            logger.info(f"Cache miss: No cached question for template_id={template_id}")
        return question

    def get_unanswered_question(self, template_id: int, user_id: int) -> Optional[Question]:
        """
        Returns a question for the given template that the user hasn't answered yet.
        """
        logger.debug(f"Looking for unanswered question for template_id={template_id}, user_id={user_id}")
        from sqlalchemy import exists
        
        # Check if a response exists for a given question and user
        stmt = exists().where(
            UserResponse.question_id == Question.question_id
        ).where(
            UserResponse.user_id == user_id
        )
        
        question = (
            self.db.query(Question)
            .filter(Question.template_id == template_id)
            .filter(~stmt)
            .first()
        )
        
        if question:
            logger.info(f"Found unanswered question_id={question.question_id} for template_id={template_id}, user_id={user_id}")
        else:
            logger.info(f"No unanswered question found for template_id={template_id}, user_id={user_id}")
        return question

    def get_by_id(self, question_id: int) -> Optional[Question]:
        logger.debug(f"Fetching question by question_id={question_id}")
        question = (
            self.db.query(Question)
            .filter(Question.question_id == question_id)
            .first()
        )
        if question:
            logger.debug(f"Found question_id={question_id}")
        else:
            logger.warning(f"Question not found: question_id={question_id}")
        return question

    def get_concept(self, concept_id: int) -> Optional[Concept]:
        logger.debug(f"Fetching concept by concept_id={concept_id}")
        concept = (
            self.db.query(Concept)
            .filter(Concept.concept_id == concept_id)
            .first()
        )
        if concept:
            logger.debug(f"Found concept_id={concept_id}")
        else:
            logger.warning(f"Concept not found: concept_id={concept_id}")
        return concept
    
    def get_template(self, template_id: int) -> Optional[Template]:
        logger.debug(f"Fetching template by template_id={template_id}")
        template = (
            self.db.query(Template)
            .filter(Template.template_id == template_id)
            .first()
        )
        if template:
            logger.debug(f"Found template_id={template_id}")
        else:
            logger.warning(f"Template not found: template_id={template_id}")
        return template

    def save_question(self, question: Question) -> Question:
        logger.info(f"Saving new question for template_id={question.template_id}")
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        logger.info(f"Successfully saved question_id={question.question_id} for template_id={question.template_id}")
        return question
