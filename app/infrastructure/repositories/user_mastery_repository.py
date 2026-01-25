from typing import Dict
from ..services.database import SessionLocal
from ..models.user_mastery import UserMastery
from .base import BaseRepository


class UserMasteryRepository(BaseRepository):

    def get_mastery(self, user_id: int, concept_id: int) -> float:
        with SessionLocal() as db:
            row = (
                db.query(UserMastery)
                .filter(
                    UserMastery.user_id == user_id,
                    UserMastery.concept_id == concept_id,
                )
                .first()
            )
            return row.mastery if row else 0.3  # BKT prior

    def get_all_masteries(self, user_id: int) -> Dict[int, float]:
        with SessionLocal() as db:
            rows = (
                db.query(UserMastery)
                .filter(UserMastery.user_id == user_id)
                .all()
            )
            return {r.concept_id: r.mastery for r in rows}

    def update_mastery(
        self,
        user_id: int,
        concept_id: int,
        mastery: float,
    ) -> None:
        with SessionLocal() as db:
            row = (
                db.query(UserMastery)
                .filter(
                    UserMastery.user_id == user_id,
                    UserMastery.concept_id == concept_id,
                )
                .first()
            )

            if row:
                row.mastery = mastery
            else:
                db.add(
                    UserMastery(
                        user_id=user_id,
                        concept_id=concept_id,
                        mastery=mastery,
                    )
                )
            db.commit()
