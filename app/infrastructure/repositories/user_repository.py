from typing import Dict, List
from sqlalchemy.orm import Session
from ..db.models import UserModel, UserAbility, UserMastery

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_global_ability(self, user_id: int) -> float:
        ability = (
            self.db.query(UserAbility)
            .filter(UserAbility.user_id == user_id)
            .first()
        )
        return ability.global_ability if ability else 0.5  # Neutral theta

    def update_global_ability(self, user_id: int, ability_val: float) -> None:
        ability = (
            self.db.query(UserAbility)
            .filter(UserAbility.user_id == user_id)
            .first()
        )
        if ability:
            ability.global_ability = ability_val
        else:
            self.db.add(UserAbility(user_id=user_id, global_ability=ability_val))
        self.db.commit()

    def get_concept_mastery(self, user_id: int) -> Dict[int, float]:
        rows = (
            self.db.query(UserMastery)
            .filter(UserMastery.user_id == user_id)
            .all()
        )
        return {row.concept_id: row.mastery for row in rows}

    def update_concept_mastery(
        self,
        user_id: int,
        concept_id: int,
        mastery: float,
    ) -> None:
        record = (
            self.db.query(UserMastery)
            .filter(
                UserMastery.user_id == user_id,
                UserMastery.concept_id == concept_id,
            )
            .first()
        )

        if record:
            record.mastery = mastery
        else:
            self.db.add(
                UserMastery(
                    user_id=user_id,
                    concept_id=concept_id,
                    mastery=mastery,
                )
            )
        self.db.commit()

    def get_prerequisites(self, concept_id: int) -> List[int]:
        # This belongs in ConceptRepo but keeping here for simplicity if needed by engine
        from ..db.models import Concept
        concept = self.db.query(Concept).filter(Concept.concept_id == concept_id).first()
        return concept.prerequisites if concept else []
