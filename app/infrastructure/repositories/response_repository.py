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

    def get_recent_responses(self, user_id: int, limit: int = 20) -> List[UserResponse]:
        return (
            self.db.query(UserResponse)
            .filter(UserResponse.user_id == user_id)
            .order_by(UserResponse.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_irt_responses(self, user_id: int) -> List[Dict]:
        rows = (
            self.db.query(UserResponse)
            .filter(UserResponse.user_id == user_id)
            .all()
        )

        return [
            {
                "correct": r.correct,
                "difficulty": r.question.difficulty if r.question else 0.5,
                "discrimination": r.question.discrimination if r.question else 1.0,
                "guessing": r.question.guessing if r.question else 0.25,
            }
            for r in rows
        ]

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
