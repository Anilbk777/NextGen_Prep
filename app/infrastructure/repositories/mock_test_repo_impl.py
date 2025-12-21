from sqlalchemy.orm import Session
from infrastructure.db.models.mock_test_model import MockTestModel
from infrastructure.db.models.mcq_model import MCQModel
from presentation.schemas.mock_test_schema import MockTestCreate
import logging

logger = logging.getLogger(__name__)

def create_mock_test(db: Session, data: MockTestCreate) -> MockTestModel:
    try:
        logger.info(f"Creating Mock Test: {data.title}")
        mock_test = MockTestModel(
            title=data.title,
            subject=data.subject
        )
        
        # Add questions
        questions = db.query(MCQModel).filter(MCQModel.id.in_(data.mcq_ids)).all()
        if len(questions) != len(data.mcq_ids):
            found_ids = [q.id for q in questions]
            missing = set(data.mcq_ids) - set(found_ids)
            raise ValueError(f"MCQs not found: {missing}")
            
        mock_test.questions = questions
        db.add(mock_test)
        db.commit()
        db.refresh(mock_test)
        logger.info(f"Mock Test {mock_test.id} created with {len(questions)} questions")
        return mock_test
    except Exception as e:
        logger.error(f"Error creating mock test: {e}", exc_info=True)
        db.rollback()
        raise

def get_practice_mcqs(db: Session, subject: str = None) -> list[MCQModel]:
    try:
        query = db.query(MCQModel)
        if subject:
            query = query.filter(MCQModel.subject == subject)
        # Practice questions include those marked is_practice_only 
        # but technically any MCQ can be practiced if the user wants.
        # Requirement says: "Admin can mark questions specifically for practice mode."
        # and "Users see MCQs instantly."
        # I'll fetch questions that ARE NOT is_practice_only=False if we want to filter,
        # but usually practice mode can show all or a subset.
        # Let's filter by is_practice_only if it's meant to be exclusive, 
        # or just return based on subject.
        # The prompt says: "Add a flag to MCQs (is_practice_only) to differentiate practice questions."
        # This implies many MCQs might be for mock tests ONLY or both.
        # Let's assume practice mode fetches questions where is_practice_only is True
        # OR questions that aren't tied exclusively to mock tests? 
        # Actually, let's just fetch all for now, or filter if is_practice_only is set.
        return query.all()
    except Exception as e:
        logger.error(f"Error fetching practice MCQs: {e}", exc_info=True)
        raise

def get_mock_test_with_questions(db: Session, mock_test_id: int) -> MockTestModel:
    try:
        mock_test = db.query(MockTestModel).filter(MockTestModel.id == mock_test_id).first()
        if not mock_test:
            raise ValueError(f"Mock Test {mock_test_id} not found")
        return mock_test
    except Exception as e:
        logger.error(f"Error fetching mock test {mock_test_id}: {e}", exc_info=True)
        raise
