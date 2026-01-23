from sqlalchemy.orm import Session
from infrastructure.db.models.mock_test_model import MockTestModel, mock_test_mcq_association
from infrastructure.db.models.mcq_model import MockTestMCQ, MockTestOption, PracticeMCQ
from infrastructure.db.models.subject_model import MockTestSubject
from presentation.schemas.mock_test_schema import MockTestBulkCreate, QuestionCreate
from infrastructure.db.models.mock_test_session import (
    MockTestSessionModel,
    MockTestSessionAnswerModel,
    MockTestSessionQuestionModel,
)
import logging

logger = logging.getLogger(__name__)


class MockTestRepository:
    """Repository for managing Mock Tests and their associated subjects and questions."""

    def __init__(self, db: Session):
        self.db = db

    def _get_or_create_subject(self, subject_name: str, mock_test_id: int) -> int:
        """Helper to get or create a MockTestSubject within a specific MockTest."""
        subject_name = subject_name.strip()
        subject = (
            self.db.query(MockTestSubject)
            .filter(
                MockTestSubject.mock_test_id == mock_test_id,
                MockTestSubject.name == subject_name,
            )
            .first()
        )

        if not subject:
            subject = MockTestSubject(name=subject_name, mock_test_id=mock_test_id)
            self.db.add(subject)
            self.db.flush()
            logger.info(
                f"Created new MockTestSubject '{subject_name}' for MockTest {mock_test_id}"
            )

        return subject.id

    def _create_mcq_with_options(
        self, question_data: QuestionCreate, subject_id: int, mock_test_id: int
    ) -> MockTestMCQ:
        """Helper to create a MockTestMCQ and its associated options."""
        mcq = MockTestMCQ(
            question_text=question_data.question_text.strip(),
            subject_id=subject_id,
            mock_test_id=mock_test_id,
        )
        self.db.add(mcq)
        self.db.flush()

        for opt_data in question_data.options:
            option = MockTestOption(
                mcq_id=mcq.id,
                option_text=opt_data.option_text.strip(),
                is_correct=opt_data.is_correct,
            )
            self.db.add(option)

        return mcq

    def get_all(self) -> list[MockTestModel]:
        """Fetch all mock tests."""
        try:
            return self.db.query(MockTestModel).all()
        except Exception as e:
            logger.error(f"Error fetching all mock tests: {e}")
            raise

    def get_by_id(self, mock_test_id: int) -> MockTestModel:
        """Fetch a mock test with its questions by ID."""
        try:
            mock_test = (
                self.db.query(MockTestModel)
                .filter(MockTestModel.id == mock_test_id)
                .first()
            )
            if not mock_test:
                raise ValueError(f"Mock Test {mock_test_id} not found")
            return mock_test
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error fetching mock test {mock_test_id}: {e}")
            raise

    def get_mock_test_with_questions(self, mock_test_id: int) -> MockTestModel:
        """Fetch a mock test with its questions by ID (Alias for get_by_id)."""
        return self.get_by_id(mock_test_id)

    def bulk_create_mock_test(
        self, data: MockTestBulkCreate, admin_id: int
    ) -> MockTestModel:
        """
        Atomically create a mock test with its subjects, questions, and options.
        """
        try:
            logger.info(
                f"Starting bulk creation of mock test: {data.title} with {len(data.questions)} questions"
            )

            # 1. Create the Mock Test header
            mock_test = MockTestModel(title=data.title.strip())
            self.db.add(mock_test)
            self.db.flush()

            subject_cache = {}  # Cache subject names to IDs for this mock test
            created_mcqs = []

            # 2. Process each question
            for idx, q_data in enumerate(data.questions, start=1):
                # Resolve subject
                subject_name = q_data.subject.strip()
                if subject_name not in subject_cache:
                    subject_cache[subject_name] = self._get_or_create_subject(
                        subject_name, mock_test.id
                    )

                subject_id = subject_cache[subject_name]

                # Create MCQ and options
                mcq = self._create_mcq_with_options(q_data, subject_id, mock_test.id)
                created_mcqs.append(mcq)

            # 3. Establish Many-to-Many relationship
            mock_test.questions = created_mcqs

            self.db.commit()
            self.db.refresh(mock_test)

            logger.info(
                f"Successfully created mock test '{data.title}' (ID: {mock_test.id}) "
                f"with {len(created_mcqs)} questions across {len(subject_cache)} subjects"
            )
            return mock_test

        except Exception as e:
            logger.error(f"Error during bulk mock test creation: {e}", exc_info=True)
            self.db.rollback()
            raise

    def delete_mock_test(self, mock_test_id: int) -> None:
        """Delete a mock test and all its associated subjects, questions, and options."""
        try:
            logger.info(f"Starting deletion of mock test {mock_test_id}")

            # 1. Delete all associated sessions first (and their dependent data)
            # Delete session answers
            self.db.query(MockTestSessionAnswerModel).filter(
                MockTestSessionAnswerModel.session_id.in_(
                    self.db.query(MockTestSessionModel.id).filter(
                        MockTestSessionModel.mock_test_id == mock_test_id
                    )
                )
            ).delete(synchronize_session=False)

            # Delete session questions
            self.db.query(MockTestSessionQuestionModel).filter(
                MockTestSessionQuestionModel.session_id.in_(
                    self.db.query(MockTestSessionModel.id).filter(
                        MockTestSessionModel.mock_test_id == mock_test_id
                    )
                )
            ).delete(synchronize_session=False)

            # Delete sessions
            self.db.query(MockTestSessionModel).filter(
                MockTestSessionModel.mock_test_id == mock_test_id
            ).delete(synchronize_session=False)

            # 2. Delete all associated questions and options
            self.db.query(MockTestOption).filter(
                MockTestOption.mcq_id.in_(
                    self.db.query(MockTestMCQ.id).filter(
                        MockTestMCQ.mock_test_id == mock_test_id
                    )
                )
            ).delete(synchronize_session=False)

            self.db.query(MockTestMCQ).filter(
                MockTestMCQ.mock_test_id == mock_test_id
            ).delete(synchronize_session=False)

            # 2. Delete all associated subjects
            self.db.query(MockTestSubject).filter(
                MockTestSubject.mock_test_id == mock_test_id
            ).delete(synchronize_session=False)

            # 3. Delete the mock test itself
            self.db.query(MockTestModel).filter(
                MockTestModel.id == mock_test_id
            ).delete(synchronize_session=False)

            self.db.commit()
            logger.info(f"Successfully deleted mock test {mock_test_id}")

        except Exception as e:
            logger.error(f"Error deleting mock test {mock_test_id}: {e}", exc_info=True)
            self.db.rollback()
            raise
