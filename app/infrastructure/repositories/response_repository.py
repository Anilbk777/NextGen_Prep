from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..db.models import UserResponse, BanditStats, Question

class ResponseRepository:
    def __init__(self, db: Session):
        self.db = db

    def store_response(self, response: UserResponse) -> UserResponse:
        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)
        return response

    def get_response(self, user_id: int, question_id: int) -> Optional[UserResponse]:
        return (
            self.db.query(UserResponse)
            .filter(
                UserResponse.user_id == user_id,
                UserResponse.question_id == question_id,
            )
            .first()
        )

    def get_recent_responses(self, user_id: int, limit: int = 20) -> List[UserResponse]:
        return (
            self.db.query(UserResponse)
            .filter(UserResponse.user_id == user_id)
            .order_by(UserResponse.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_irt_responses(self, user_id: int) -> List[Dict]:
        """
        Build a history of responses with IRT-style parameters.

        Note: the current schema does not store difficulty/discrimination/guessing
        on the Question table. Instead, we derive difficulty from the associated
        Template's target_difficulty and use reasonable defaults for the other
        parameters.
        """
        rows = (
            self.db.query(UserResponse)
            .filter(UserResponse.user_id == user_id)
            .all()
        )

        history: List[Dict] = []
        for r in rows:
            question = r.question
            template = question.template if question is not None else None
            base_difficulty = (
                template.target_difficulty
                if template is not None and template.target_difficulty is not None
                else 0.5
            )
            # Map [0,1] difficulty onto a rough [-3,3] IRT difficulty scale
            irt_difficulty = (base_difficulty - 0.5) * 6.0

            history.append(
                {
                    "correct": r.correct,
                    "difficulty": irt_difficulty,
                    "discrimination": 1.0,
                    "guessing": 0.25,
                }
            )

        return history

    def get_bandit_stats(self, user_id: int) -> Dict[int, Dict[str, float]]:
        stats = (
            self.db.query(BanditStats)
            .filter(BanditStats.user_id == user_id)
            .all()
        )
        return {
            s.template_id: {"alpha": s.alpha, "beta": s.beta}
            for s in stats
        }

    def update_bandit_stats(
        self,
        user_id: int,
        template_id: int,
        alpha: float,
        beta: float,
    ) -> None:
        stat = (
            self.db.query(BanditStats)
            .filter(
                BanditStats.user_id == user_id,
                BanditStats.template_id == template_id,
            )
            .first()
        )

        if not stat:
            stat = BanditStats(
                user_id=user_id,
                template_id=template_id,
                alpha=alpha,
                beta=beta,
            )
            self.db.add(stat)
        else:
            stat.alpha = alpha
            stat.beta = beta
        
        self.db.commit()
