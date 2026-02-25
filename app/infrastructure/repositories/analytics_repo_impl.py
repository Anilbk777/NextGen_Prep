from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, union_all, literal_column, case, literal

from app.infrastructure.db.models import (
    AttemptModel,
    PracticeMCQ,
    Topic,
    PracticeSubject,
    MockTestSessionModel,
    MockTestSessionQuestionModel,
    MockTestSessionAnswerModel,
    MockTestOption,
    MockTestSubject,
)


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_daily_subject_progress(
        self,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate daily accuracy and attempts per subject for given user.

        Uses only the specified tables:
        - Practice: attempts -> practice_mcqs -> topics -> practice_subjects
        - Mock: mock_test_sessions -> mock_test_session_questions -> mock_test_session_answers -> mock_test_options -> mock_test_subjects
        """
        # --- Practice mode select ---
        practice_sel = (
            select(
                func.date(AttemptModel.attempted_at).label("date"),
                Topic.subject_id.label("subject_id"),
                literal("practice").label("source"),
                case((AttemptModel.is_correct == True, 1), else_=0).label("correct"),
                literal_column("1").label("attempts"),
            )
            .select_from(AttemptModel)
            .join(PracticeMCQ, AttemptModel.mcq_id == PracticeMCQ.id)
            .join(Topic, PracticeMCQ.topic_id == Topic.id)
            .where(AttemptModel.user_id == user_id)
        )

        # --- Mock test mode select ---
        # join answers -> session (to filter by user) -> session_question (to get subject)
        # join selected option to MockTestOption to determine correctness
        mock_sel = (
            select(
                func.date(MockTestSessionAnswerModel.answered_at).label("date"),
                MockTestSessionQuestionModel.subject_id.label("subject_id"),
                literal("mock").label("source"),
                case((MockTestOption.is_correct == True, 1), else_=0).label("correct"),
                literal_column("1").label("attempts"),
            )
            .select_from(MockTestSessionAnswerModel)
            .join(
                MockTestSessionModel,
                MockTestSessionAnswerModel.session_id == MockTestSessionModel.id,
            )
            .join(
                MockTestSessionQuestionModel,
                (
                    MockTestSessionQuestionModel.session_id
                    == MockTestSessionAnswerModel.session_id
                )
                & (
                    MockTestSessionQuestionModel.mcq_id
                    == MockTestSessionAnswerModel.mcq_id
                ),
            )
            .join(
                MockTestOption,
                MockTestSessionAnswerModel.selected_option_id == MockTestOption.id,
            )
            .where(MockTestSessionModel.user_id == user_id)
        )

        # Apply date filters if provided
        if start_date:
            practice_sel = practice_sel.where(
                func.date(AttemptModel.attempted_at) >= start_date
            )
            mock_sel = mock_sel.where(
                func.date(MockTestSessionAnswerModel.answered_at) >= start_date
            )

        if end_date:
            practice_sel = practice_sel.where(
                func.date(AttemptModel.attempted_at) <= end_date
            )
            mock_sel = mock_sel.where(
                func.date(MockTestSessionAnswerModel.answered_at) <= end_date
            )

        # Union practice and mock selects
        union_q = union_all(practice_sel, mock_sel).alias("u")

        agg = (
            select(
                union_q.c.date.label("date"),
                union_q.c.subject_id.label("subject_id"),
                union_q.c.source.label("source"),
                (
                    func.sum(union_q.c.correct)
                    / func.nullif(func.count(union_q.c.attempts), 0)
                ).label("accuracy"),
                func.count(union_q.c.attempts).label("attempts"),
            )
            .group_by(union_q.c.date, union_q.c.subject_id, union_q.c.source)
            .order_by(union_q.c.date)
        )

        rows = self.db.execute(agg).fetchall()

        results: List[Dict[str, Any]] = []
        for r in rows:
            results.append(
                {
                    "date": (
                        r.date.isoformat()
                        if hasattr(r.date, "isoformat")
                        else str(r.date)
                    ),
                    "subject_id": r.subject_id,
                    "subject_source": r.source,
                    "subject_key": f"{r.source}:{r.subject_id}",
                    "accuracy": float(r.accuracy) if r.accuracy is not None else 0.0,
                    "attempts": int(r.attempts),
                }
            )

        return results
