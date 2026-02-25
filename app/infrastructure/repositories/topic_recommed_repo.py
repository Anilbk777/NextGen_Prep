
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
import logging

from ..db.models.user_mastery_model import UserMastery 
from ..db.models.concept_model import Concept
from ..db.models.topic_model import Topic

logger = logging.getLogger(__name__)


class TopicRecommendRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_topic_mastery_aggregates(self, user_id: int):
        """
        Returns:
        topic_id,
        topic_name,
        total_concepts,
        known_concepts,
        sum_mastery
        """

        try:
            subquery_total = (
                self.db.query(
                    Concept.topic_id,
                    func.count(Concept.concept_id).label("total_concepts"),
                )
                .group_by(Concept.topic_id)
                .subquery()
            )

            subquery_known = (
                self.db.query(
                    Concept.topic_id,
                    func.count(UserMastery.id).label("known_concepts"),
                    func.coalesce(func.sum(UserMastery.mastery), 0.0).label(
                        "sum_mastery"
                    ),
                )
                .join(
                    UserMastery,
                    and_(
                        UserMastery.concept_id == Concept.concept_id,
                        UserMastery.user_id == user_id,
                    ),
                    isouter=True,
                )
                .group_by(Concept.topic_id)
                .subquery()
            )

            results = (
                self.db.query(
                    Topic.id.label("topic_id"),
                    Topic.name.label("topic_name"),
                    subquery_total.c.total_concepts,
                    func.coalesce(subquery_known.c.known_concepts, 0).label(
                        "known_concepts"
                    ),
                    func.coalesce(subquery_known.c.sum_mastery, 0.0).label(
                        "sum_mastery"
                    ),
                )
                .join(subquery_total, Topic.id == subquery_total.c.topic_id)
                .join(subquery_known, Topic.id == subquery_known.c.topic_id)
                .all()
            )

            return results

        except Exception as e:
            logger.exception("Failed to fetch topic aggregates: %s", e)
            raise

    def get_user_mastery_count(self, user_id: int) -> int:
        return (
            self.db.query(func.count(UserMastery.id))
            .filter(UserMastery.user_id == user_id)
            .scalar()
        )

    def get_foundational_topics(self):
        return self.db.query(Topic).order_by(Topic.order_index.asc()).limit(3).all()

    def prerequisites_satisfied(
        self, user_id: int, topic_id: int, threshold: float
    ) -> bool:
        """
        Checks if all prerequisite concepts in this topic are mastered.
        """

        concepts = self.db.query(Concept).filter(Concept.topic_id == topic_id).all()

        for concept in concepts:
            if not concept.prerequisites:
                continue

            for prereq_id in concept.prerequisites:
                mastery = (
                    self.db.query(UserMastery.mastery)
                    .filter(
                        UserMastery.user_id == user_id,
                        UserMastery.concept_id == prereq_id,
                    )
                    .scalar()
                )

                if mastery is None or mastery < threshold:
                    return False

        return True
