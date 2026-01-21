import logging
from fastapi import HTTPException
from datetime import datetime
from typing import Dict, Any, List
from app.presentation.schemas.practice_schemas import (
    PracticeSessionStartOut,
    PracticeQuestionOut,
    PracticeAnswerOut,
    PracticeSessionSummaryOut,
    PracticeOptionOut
)

logger = logging.getLogger(__name__)

class PracticeSessionService:
    def __init__(
        self,
        session_repo,   # PracticeSessionRepository
        question_repo,  # QuestionRepository
        attempt_repo,   # AttemptRepository
        db              # SQLAlchemy session
    ):
        self.session_repo = session_repo
        self.question_repo = question_repo
        self.attempt_repo = attempt_repo
        self.db = db

    # -------------------------
    # 1️⃣ Start session (4–3–3)
    # -------------------------
    def start_session(self, user_id: int, topic_id: int) -> Dict[str, Any]:
        logger.info(f"Starting practice session for user {user_id} on topic {topic_id}")
        
        easy = self.question_repo.get_random_by_difficulty(topic_id, "easy", 4)
        medium = self.question_repo.get_random_by_difficulty(topic_id, "medium", 3)
        hard = self.question_repo.get_random_by_difficulty(topic_id, "hard", 3)

        # Ensure enough MCQs
        if len(easy) < 4 or len(medium) < 3 or len(hard) < 3:
            logger.warning(f"Not enough MCQs for topic {topic_id}: Easy({len(easy)}/4), Medium({len(medium)}/3), Hard({len(hard)}/3)")
            raise HTTPException(status_code=400, detail="Not enough MCQs for this topic")

        # Order: Easy → Medium → Hard
        ordered_mcqs = easy + medium + hard

        # Create session
        session = self.session_repo.create(user_id, topic_id)
        self.session_repo.add_questions(session.id, ordered_mcqs)

        logger.info(f"Practice session {session.id} started successfully for user {user_id}")
        return {
            "session_id": session.id,
            "total_questions": session.total_questions
        }

    # -------------------------
    # 2️⃣ Get current question
    # -------------------------
    def get_current_question(self, session_id: int, user_id: int) -> Dict[str, Any]:
        logger.debug(f"Fetching current question for session {session_id}, user {user_id}")
        session = self.session_repo.get_active(session_id, user_id)

        if session.current_index >= session.total_questions:
            logger.warning(f"Session {session_id} already completed for user {user_id}")
            raise HTTPException(status_code=400, detail="Session already completed")

        # Get question for current index
        try:
            question_link = session.questions[session.current_index]
            mcq = question_link.mcq
        except IndexError:
            logger.error(f"Index mismatch in session {session_id}: current_index={session.current_index}, total={session.total_questions}")
            raise HTTPException(status_code=500, detail="Internal session state error")

        return {
            "question_id": mcq.id,
            "question_text": mcq.question_text,
            "options": [{"id": opt.id, "text": opt.option_text} for opt in mcq.options],
            "order_index": question_link.order_index
        }

    # -------------------------
    # 3️⃣ Submit answer
    # -------------------------
    def submit_answer(
        self,
        session_id: int,
        user_id: int,
        question_id: int,
        selected_option_id: int
    ) -> Dict[str, Any]:
        logger.info(f"Submitting answer for session {session_id}, question {question_id}, option {selected_option_id}")
        session = self.session_repo.get_active(session_id, user_id)

        # Current question
        try:
            current_link = session.questions[session.current_index]
            mcq = current_link.mcq
        except IndexError:
            logger.error(f"Index mismatch during submission in session {session_id}: current_index={session.current_index}")
            raise HTTPException(status_code=500, detail="Internal session state error")

        if mcq.id != question_id:
            logger.warning(f"Question mismatch in session {session_id}. Expected {mcq.id}, got {question_id}")
            raise HTTPException(status_code=400, detail="Question mismatch")

        # Validate option
        selected_option = self.question_repo.get_option(selected_option_id)
        if not selected_option:
            logger.warning(f"Invalid option {selected_option_id} submitted for question {question_id}")
            raise HTTPException(status_code=400, detail="Invalid option")

        is_correct = selected_option.is_correct

        # Save attempt
        self.attempt_repo.create(
            user_id=user_id,
            session_id=session.id,
            mcq_id=mcq.id,
            selected_option_id=selected_option.id,
            is_correct=is_correct
        )

        # Advance session
        try:
            session.current_index += 1
            if session.current_index >= session.total_questions:
                logger.info(f"Session {session_id} completed for user {user_id}")
                self.session_repo.close(session)
            else:
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error advancing session {session_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error updating session state")

        # Find correct option id
        correct_option = next((opt for opt in mcq.options if opt.is_correct), None)
        
        if not correct_option:
             logger.error(f"MCQ {mcq.id} has no correct option defined")
             raise HTTPException(status_code=500, detail="Data integrity error: No correct option found")

        return {
            "is_correct": is_correct,
            "correct_option_id": correct_option.id,
            "explanation": mcq.explanation
        }

    # -------------------------
    # 4️⃣ Session summary
    # -------------------------
    def get_summary(self, session_id: int, user_id: int) -> Dict[str, Any]:
        logger.info(f"Generating summary for session {session_id}, user {user_id}")
        attempts = self.attempt_repo.get_by_session(session_id, user_id)

        total = len(attempts)
        correct = sum(a.is_correct for a in attempts)
        incorrect = total - correct

        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect
        }
