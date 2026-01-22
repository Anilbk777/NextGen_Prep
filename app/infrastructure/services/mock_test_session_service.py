from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.db.models.mock_test_session import MockTestSessionModel
from infrastructure.repositories.mock_test_conc_repo import MockTestRepositoryImpl

logger = logging.getLogger(__name__)

class MockTestSessionService:
    SESSION_DURATION = timedelta(hours=2)

    def __init__(self, db: Session, repo: MockTestRepositoryImpl):
        self.db = db
        self.repo = repo

    # --------------------------------------------------
    # 1. Start mock test session
    # --------------------------------------------------
    def start_session(self, user_id: int, mock_test_id: int) -> MockTestSessionModel:
        """
        Starts a new mock test session or returns an existing active one.
        Initializes the session with questions from the mock test structure.
        """
        try:
            logger.info(f"User {user_id} requesting to start mock test {mock_test_id}")
            
            # Prevent multiple active sessions for the same user and test
            active = self.repo.get_active_session_for_user_test(self.db, user_id, mock_test_id)
            if active:
                logger.info(f"User {user_id} already has an active session {active.id} for mock test {mock_test_id}. Returning existing session.")
                return active

            now = datetime.now(timezone.utc)
            ends_at = now + self.SESSION_DURATION

            logger.info(f"Creating new session for user {user_id}, ends at {ends_at}")
            session = self.repo.create_session(
                db=self.db,
                user_id=user_id,
                mock_test_id=mock_test_id,
                started_at=now,
                expires_at=ends_at,
            )

            # Fix question order: subject-wise
            logger.info(f"Fetching mock test structure for ID {mock_test_id} to populate session questions")
            mock_test = self.repo.get_mock_test_with_subjects(self.db, mock_test_id)
            if not mock_test:
                logger.error(f"Mock test {mock_test_id} structure not found!")
                raise ValueError(f"Mock test {mock_test_id} not found")

            session_questions_data = []
            order_index = 0
            for subject in mock_test.subjects:
                for mcq in subject.mcqs:
                    session_questions_data.append({
                        'mcq_id': mcq.id,
                        'subject_id': subject.id,
                        'order_index': order_index
                    })
                    order_index += 1

            if session_questions_data:
                self.repo.add_session_questions(
                    db=self.db,
                    session_id=session.id,
                    questions_data=session_questions_data
                )
            else:
                logger.warning(f"Mock test {mock_test_id} has no questions configured.")

            # self.db.commit() # Repository methods handle commit, but service orchestrating multiple steps might need final commit if implicit. 
            # Repo methods doing db.commit() individually.
            
            logger.info(f"Session {session.id} started successfully.")
            return session

        except ValueError as e:
            logger.error(f"Validation error starting session: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error starting session: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting session: {e}", exc_info=True)
            raise

    # --------------------------------------------------
    # 2. Get questions (free navigation)
    # --------------------------------------------------
    def get_questions(self, session_id: int, user_id: int):
        """
        Retrieves all questions for a validated active session.
        Attaches existing answers to the question objects.
        """
        try:
            logger.info(f"User {user_id} fetching questions for session {session_id}")
            session = self._validate_session(session_id, user_id)
            questions = self.repo.get_session_questions(self.db, session.id)
            
            # Fetch answers and map them to mcq_id for quick lookup
            answers = self.repo.get_session_answers(self.db, session.id)
            answer_map = {a.mcq_id: a for a in answers}
            
            # Attach answer if exists
            for q in questions:
                q.answer = answer_map.get(q.mcq_id)
                
            return questions
        except Exception as e:
            logger.error(f"Error fetching questions for session {session_id}: {e}", exc_info=True)
            raise

    # --------------------------------------------------
    # 3. Save / update answer (overwrite allowed)
    # --------------------------------------------------
    def save_answer(
        self,
        session_id: int,
        user_id: int,
        mcq_id: int,
        selected_option_id: Optional[int],
    ) -> None:
        """
        Saves or updates a user's answer for a specific question in the session.
        """
        try:
            # logger.debug(f"Saving answer: session={session_id}, mcq={mcq_id}, opt={selected_option_id}") # Debug level for frequent actions
            session = self._validate_session(session_id, user_id)

            self.repo.upsert_answer(
                db=self.db,
                session_id=session.id,
                mcq_id=mcq_id,
                selected_option_id=selected_option_id,
            )
            # Repo handles commit
        except Exception as e:
            logger.error(f"Error saving answer for session {session_id}: {e}", exc_info=True)
            raise

    # --------------------------------------------------
    # 4. Submit mock test manually
    # --------------------------------------------------
    def submit(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """
        Submits the mock test session and returns evaluation results.
        """
        try:
            logger.info(f"User {user_id} submitting session {session_id}")
            session = self._validate_session(session_id, user_id)

            self.repo.mark_session_submitted(self.db, session.id)

            result = self._evaluate(session.id)
            
            logger.info(f"Session {session_id} submitted. Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error submitting session {session_id}: {e}", exc_info=True)
            raise

    # --------------------------------------------------
    # 5. Auto-submit on expiry
    # --------------------------------------------------
    def auto_submit_if_expired(self, session_id: int) -> None:
        """
        Checks if a session is expired and auto-submits it if necessary.
        """
        try:
            session = self.repo.get_session_by_id(self.db, session_id)

            if not session or not session.is_active:
                return

            # Ensure timezone awareness compatibility
            now = datetime.now(timezone.utc)
            ends_at = session.ends_at
            if ends_at.tzinfo is None:
                 ends_at = ends_at.replace(tzinfo=timezone.utc)

            if now > ends_at:
                logger.info(f"Auto-submitting expired session {session_id}")
                self.repo.mark_session_submitted(self.db, session.id)
        except Exception as e:
            logger.error(f"Error in auto-submit check for session {session_id}: {e}", exc_info=True)
            # Don't raise here to avoid blocking other read operations if this background check fails

    # --------------------------------------------------
    # Internal: evaluation logic
    # --------------------------------------------------
    def _evaluate(self, session_id: int) -> Dict[str, Any]:
        answers = self.repo.get_session_answers(self.db, session_id)

        correct = 0
        incorrect = 0
        skipped = 0

        for ans in answers:
            if ans.selected_option_id is None:
                skipped += 1
            elif ans.selected_option and ans.selected_option.is_correct:
                correct += 1
            else:
                incorrect += 1

        # We need total questions count. 
        # Either count from answers (if we assume entry for every question exists, which might not be true if upsert only happens on answer)
        # OR fetch session questions count.
        # Current implementation of upsert_answer implies answers rows might not exist for unvisited questions? 
        # Logic in start_session creates *questions* mapping, but NOT *answers* rows.
        # So `get_session_answers` only returns questions that were *answered* (or at least attempted/saved).
        # Skipped questions (never saved) won't be in `answers`.
        
        # To get accurate stats, we need total questions in the session.
        session_questions = self.repo.get_session_questions(self.db, session_id)
        total = len(session_questions)
        
        # Recalculate based on total
        answered_count = correct + incorrect # + skipped (if saved as None)
        
        # Any question not in 'answers' list is implicitly skipped?
        # OR if 'answers' includes rows with None options?
        # The `upsert_answer` creates a row. If user never touches a question, no row exists.
        
        # Better logic:
        # Create a map of answered questions
        answered_map = {a.mcq_id: a for a in answers}
        
        correct = 0
        incorrect = 0
        skipped = 0
        
        for q in session_questions:
            ans = answered_map.get(q.mcq_id)
            if not ans:
                skipped += 1
            elif ans.selected_option_id is None:
                skipped += 1
            elif ans.selected_option and ans.selected_option.is_correct:
                correct += 1
            else:
                incorrect += 1
                
        return {
            "total_questions": total,
            "correct": correct,
            "incorrect": incorrect,
            "skipped": skipped,
        }

    # --------------------------------------------------
    # Internal: session guard
    # --------------------------------------------------
    def _validate_session(
        self, session_id: int, user_id: int
    ) -> MockTestSessionModel:
        session = self.repo.get_session_by_id(self.db, session_id)

        if not session:
            logger.warning(f"Session {session_id} lookup failed during validation")
            raise ValueError("Session not found")

        if session.user_id != user_id:
            logger.warning(f"Unauthorized access attempt by user {user_id} to session {session_id}")
            raise ValueError("Unauthorized access")

        if session.is_submitted:
            logger.info(f"Session {session_id} is already submitted")
            raise ValueError("Session already submitted")

        # Timezone check
        now = datetime.now(timezone.utc)
        ends_at = session.ends_at
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)

        if now > ends_at:
            logger.info(f"Session {session_id} expired during validation")
            self.auto_submit_if_expired(session.id)
            raise ValueError("Session expired")

        return session
