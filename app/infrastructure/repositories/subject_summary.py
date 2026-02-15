# from sqlalchemy import func, case
# from sqlalchemy.orm import Session

# from infrastructure.db.models.attempt_model import AttemptModel
# from infrastructure.db.models.mcq_model import PracticeMCQ
# from infrastructure.db.models.subject_model import PracticeSubject
# from infrastructure.db.models.topic_model import Topic


# class SubjectSummaryRepository:

#     def __init__(self, db: Session):
#         self.db = db

#     def fetch_subject_summary(self, user_id: int):

#         total_correct_case = func.sum(
#             case((AttemptModel.is_correct == True, 1), else_=0)
#         )

#         query = (
#             self.db.query(
#                 PracticeSubject.id.label("subject_id"),
#                 PracticeSubject.name.label("subject_name"),
#                 func.count(func.distinct(PracticeMCQ.id)).label("total_questions"),
#                 func.count(AttemptModel.id).label("total_attempted"),
#                 func.coalesce(total_correct_case, 0).label("total_correct"),
#             )
#             .outerjoin(Topic, Topic.subject_id == PracticeSubject.id)
#             .outerjoin(PracticeMCQ, PracticeMCQ.topic_id == Topic.id)
#             .outerjoin(
#                 AttemptModel,
#                 (AttemptModel.mcq_id == PracticeMCQ.id)
#                 & (AttemptModel.user_id == user_id),
#             )
#             .group_by(PracticeSubject.id)
#         )

from sqlalchemy import func, case, literal_column
from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased

from ..db.models.attempt_model import AttemptModel
from ..db.models.mcq_model import PracticeMCQ
from ..db.models.subject_model import PracticeSubject
from ..db.models.topic_model import Topic

from ..db.models.mcq_model import MockTestOption, MockTestMCQ
from ..db.models.mock_test_session import (
    MockTestSessionAnswerModel,
    MockTestSessionModel,
)
from ..db.models.subject_model import MockTestSubject

from typing import List


class SubjectSummaryRepository:

    def __init__(self, db: Session):
        self.db = db

    def fetch_subject_summary(self, user_id: int):

        # ==========================
        # PRACTICE QUERY
        # ==========================

        practice_correct_case = func.sum(
            case((AttemptModel.is_correct == True, 1), else_=0)
        )

        practice_query = (
            self.db.query(
                PracticeSubject.name.label("subject_name"),
                func.count(func.distinct(PracticeMCQ.id)).label("total_questions"),
                func.count(AttemptModel.id).label("total_attempted"),
                func.coalesce(practice_correct_case, 0).label("total_correct"),
            )
            .outerjoin(Topic, Topic.subject_id == PracticeSubject.id)
            .outerjoin(PracticeMCQ, PracticeMCQ.topic_id == Topic.id)
            .outerjoin(
                AttemptModel,
                (AttemptModel.mcq_id == PracticeMCQ.id)
                & (AttemptModel.user_id == user_id),
            )
            .group_by(PracticeSubject.name)
        )

        # ==========================
        # MOCK TEST QUERY
        # ==========================


        mock_attempted_case = func.sum(
            case(((MockTestSessionModel.user_id == user_id), 1), else_=0)
        )

        mock_correct_case = func.sum(
            case(
                (
                    (MockTestSessionModel.user_id == user_id)
                    & (MockTestOption.is_correct == True),
                    1,
                ),
                else_=0,
            )
        )

        mock_query = (
            self.db.query(
                MockTestSubject.name.label("subject_name"),
                func.count(func.distinct(MockTestMCQ.id)).label("total_questions"),
                func.coalesce(mock_attempted_case, 0).label("total_attempted"),
                func.coalesce(mock_correct_case, 0).label("total_correct"),
            )
            .outerjoin(MockTestMCQ, MockTestMCQ.subject_id == MockTestSubject.id)
            .outerjoin(
                MockTestSessionAnswerModel,
                MockTestSessionAnswerModel.mcq_id == MockTestMCQ.id,
            )
            .outerjoin(
                MockTestSessionModel,
                (MockTestSessionModel.id == MockTestSessionAnswerModel.session_id),
            )
            .outerjoin(
                MockTestOption,
                MockTestOption.id == MockTestSessionAnswerModel.selected_option_id,
            )
            .group_by(MockTestSubject.name)
        )

        # ==========================
        # UNION BOTH
        # ==========================

        union_query = practice_query.union_all(mock_query).subquery()

        final_query = self.db.query(
            union_query.c.subject_name,
            func.sum(union_query.c.total_questions).label("total_questions"),
            func.sum(union_query.c.total_attempted).label("total_attempted"),
            func.sum(union_query.c.total_correct).label("total_correct"),
        ).group_by(union_query.c.subject_name)

        results = final_query.all()

        return [
            {
                "subject_name": row.subject_name,
                "total_questions": int(row.total_questions or 0),
                "total_attempted": int(row.total_attempted or 0),
                "total_correct": int(row.total_correct or 0),
            }
            for row in results
        ]


if __name__ == "__main__":
    from app.presentation.dependencies import get_db

    db = next(get_db())

    obj = SubjectSummaryRepository(db)
    result = obj.fetch_subject_summary(1)
    print(result)
