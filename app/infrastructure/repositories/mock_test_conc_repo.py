import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.repository_interface.mock_test_interface import MockTestRepository
from infrastructure.db.models.mock_test_model import MockTestModel
from infrastructure.db.models.subject_model import MockTestSubject
from infrastructure.db.models.mock_test_session import (
    MockTestSessionModel,
    MockTestSessionAnswerModel,
    MockTestSessionQuestionModel,
)

logger = logging.getLogger(__name__)


class MockTestRepositoryImpl(MockTestRepository):
    """
    Implementation of the MockTestRepository interface.
    Handles database operations for Mock Tests, Sessions, and Answers.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_mock_test_with_subjects(self, db: Session, mock_test_id: int):
        """
        Fetches the MockTest with its Subjects eagerly loaded.
        Replacing get_mock_test_structure / get_mock_test_by_id effectively.
        """
        try:
            logger.info(f"Fetching mock test {mock_test_id} with subjects")
            mock_test = (
                db.query(MockTestModel)
                .options(joinedload(MockTestModel.subjects).joinedload(MockTestSubject.mcqs)) # Eager load subjects AND mcqs
                .filter(MockTestModel.id == mock_test_id)
                .first()
            )
            if not mock_test:
                logger.warning(f"Mock test with ID {mock_test_id} not found.")
            return mock_test
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching mock test {mock_test_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching mock test {mock_test_id}: {e}", exc_info=True)
            raise

    def create_session(
        self,
        db: Session,
        user_id: int,
        mock_test_id: int,
        started_at: datetime,
        expires_at: datetime,
    ):
        try:
            logger.info(f"Creating session for user {user_id} on mock test {mock_test_id}")
            session = MockTestSessionModel(
                user_id=user_id,
                mock_test_id=mock_test_id,
                started_at=started_at,
                ends_at=expires_at,
                is_active=True,
                is_submitted=False,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            logger.info(f"Session created successfully with ID: {session.id}")
            return session
        except SQLAlchemyError as e:
            logger.error(f"Database error creating session: {e}", exc_info=True)
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating session: {e}", exc_info=True)
            db.rollback()
            raise

    def add_session_questions(
        self,
        db: Session,
        session_id: int,
        questions_data: List[Dict[str, Any]],
    ):
        """
        Bulk inserts session questions (mcq order mapping).
        questions_data should be a list of dicts with:
        {'mcq_id': int, 'subject_id': int, 'order_index': int}
        """
        try:
            logger.info(f"Adding {len(questions_data)} questions to session {session_id}")
            session_questions = []
            for q in questions_data:
                sq = MockTestSessionQuestionModel(
                    session_id=session_id,
                    mcq_id=q['mcq_id'],
                    subject_id=q['subject_id'],
                    order_index=q['order_index']
                )
                session_questions.append(sq)
            
            db.add_all(session_questions)
            db.commit()
            logger.info(f"Successfully added questions to session {session_id}")
        except SQLAlchemyError as e:
            logger.error(f"Database error adding session questions: {e}", exc_info=True)
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding session questions: {e}", exc_info=True)
            db.rollback()
            raise

    def get_active_session(self, db: Session, session_id: int, user_id: int):
        try:
            logger.info(f"Fetching active session {session_id} for user {user_id}")
            session = (
                db.query(MockTestSessionModel)
                .filter(
                    MockTestSessionModel.id == session_id,
                    MockTestSessionModel.user_id == user_id,
                    MockTestSessionModel.is_active == True,
                )
                .first()
            )
            if not session:
                logger.warning(f"Active session {session_id} for user {user_id} not found.")
            return session
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching active session: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching active session: {e}", exc_info=True)
            raise

    def get_active_session_for_user_test(self, db: Session, user_id: int, mock_test_id: int):
        """
        Checks if there is any active session for a specific user and mock test.
        """
        try:
            logger.info(f"Checking existing active session for user {user_id} on test {mock_test_id}")
            session = (
                db.query(MockTestSessionModel)
                .filter(
                    MockTestSessionModel.user_id == user_id,
                    MockTestSessionModel.mock_test_id == mock_test_id,
                    MockTestSessionModel.is_active == True,
                )
                .first()
            )
            return session
        except SQLAlchemyError as e:
            logger.error(f"Database error checking active session: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error checking active session: {e}", exc_info=True)
            raise

    def get_session_questions(self, db: Session, session_id: int):
        try:
            logger.info(f"Fetching questions for session {session_id}")
            questions = (
                db.query(MockTestSessionQuestionModel)
                .options(
                    joinedload(MockTestSessionQuestionModel.mcq), # Load MCQ details
                    joinedload(MockTestSessionQuestionModel.subject) # Load Subject details
                )
                .filter(MockTestSessionQuestionModel.session_id == session_id)
                .order_by(MockTestSessionQuestionModel.order_index)
                .all()
            )
            return questions
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching session questions: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching session questions: {e}", exc_info=True)
            raise

    def upsert_answer(
        self,
        db: Session,
        session_id: int,
        mcq_id: int,
        selected_option_id: Optional[int],
    ):
        try:
            logger.info(f"Upserting answer for session {session_id}, mcq {mcq_id}")
            answer = (
                db.query(MockTestSessionAnswerModel)
                .filter(
                    MockTestSessionAnswerModel.session_id == session_id,
                    MockTestSessionAnswerModel.mcq_id == mcq_id,
                )
                .first()
            )

            if answer:
                answer.selected_option_id = selected_option_id
                answer.answered_at = datetime.utcnow()
            else:
                answer = MockTestSessionAnswerModel(
                    session_id=session_id,
                    mcq_id=mcq_id,
                    selected_option_id=selected_option_id,
                    answered_at=datetime.utcnow()
                )
                db.add(answer)

            db.commit()
            return answer
        except SQLAlchemyError as e:
            logger.error(f"Database error upserting answer: {e}", exc_info=True)
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error upserting answer: {e}", exc_info=True)
            db.rollback()
            raise

    def get_session_answers(self, db: Session, session_id: int):
        try:
            logger.info(f"Fetching answers for session {session_id}")
            answers = (
                db.query(MockTestSessionAnswerModel)
                .options(joinedload(MockTestSessionAnswerModel.selected_option)) # Load option for evaluation
                .filter(MockTestSessionAnswerModel.session_id == session_id)
                .all()
            )
            return answers
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching answers for session {session_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching answers for session {session_id}: {e}", exc_info=True)
            raise

    def mark_session_submitted(self, db: Session, session_id: int):
        try:
            logger.info(f"Marking session {session_id} as submitted")
            session = (
                db.query(MockTestSessionModel)
                .filter(MockTestSessionModel.id == session_id)
                .first()
            )

            if session:
                session.is_submitted = True
                session.is_active = False
                db.commit()
                logger.info(f"Session {session_id} marked as submitted.")
            else:
                logger.warning(f"Session {session_id} not found to mark submitted.")
            return session
        except SQLAlchemyError as e:
            logger.error(f"Database error marking session submitted: {e}", exc_info=True)
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error marking session submitted: {e}", exc_info=True)
            db.rollback()
            raise

    def get_session_by_id(self, db: Session, session_id: int):
        try:
            logger.info(f"Fetching session info for session {session_id}")
            session = (
                db.query(MockTestSessionModel)
                .options(joinedload(MockTestSessionModel.mock_test)) # Eager load mock test just in case
                .filter(MockTestSessionModel.id == session_id)
                .first()
            )
            if not session:
                logger.warning(f"Session {session_id} not found.")
            return session
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching session {session_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching session {session_id}: {e}", exc_info=True)
            raise
