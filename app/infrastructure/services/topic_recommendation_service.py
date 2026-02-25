# # services/topic_recommendation_service.py

# from typing import List
# import logging
# from math import exp
# from datetime import datetime

# # from  schemas.recommendation_schema import TopicRecommendation
# # from app.repositories.topic_repository import TopicRepository
# from ..repositories.topic_recommed_repo import TopicRecommendRepository
# from app.presentation.schemas.recommendation_schema import TopicRecommendation
# logger = logging.getLogger(__name__)

# PRIOR = 0.5
# ALPHA = 3
# MIN_COVERAGE = 0.3
# PREREQ_THRESHOLD = 0.6
# DECAY_LAMBDA = 0.01


# class TopicRecommendationService:

#     def __init__(self, repository: TopicRecommendRepository):
#         self.repository = repository

#     def recommend_topics(self, user_id: int) -> List[TopicRecommendation]:

#         mastery_count = self.repository.get_user_mastery_count(user_id)

#         # 🔹 Cold Start
#         if mastery_count == 0:
#             logger.info("Cold start for user %s", user_id)

#             foundational_topics = self.repository.get_foundational_topics()

#             return [
#                 TopicRecommendation(
#                     topic_id=t.id,
#                     topic_name=t.name,
#                     topic_mastery=0.0,
#                     coverage=0.0,
#                     weakness_score=0.0,
#                     reason="cold_start",
#                 )
#                 for t in foundational_topics
#             ]

#         aggregates = self.repository.get_topic_mastery_aggregates(user_id)

#         recommendations = []

#         for agg in aggregates:

#             if agg.total_concepts == 0:
#                 continue

#             coverage = agg.known_concepts / agg.total_concepts

#             # Bayesian smoothing
#             topic_mastery = (agg.sum_mastery + ALPHA * PRIOR) / (
#                 agg.known_concepts + ALPHA
#             )

#             confidence = coverage

#             weakness_score = (1 - topic_mastery) * confidence

#             if coverage < MIN_COVERAGE:
#                 continue

#             if not self.repository.prerequisites_satisfied(
#                 user_id=user_id, topic_id=agg.topic_id, threshold=PREREQ_THRESHOLD
#             ):
#                 continue

#             recommendations.append(
#                 TopicRecommendation(
#                     topic_id=agg.topic_id,
#                     topic_name=agg.topic_name,
#                     topic_mastery=round(topic_mastery, 3),
#                     coverage=round(coverage, 3),
#                     weakness_score=round(weakness_score, 3),
#                     reason="weak_topic",
#                 )
#             )

#         recommendations.sort(key=lambda x: x.weakness_score, reverse=True)

#         return recommendations


# =================================================================================================================


# services/topic_recommendation_service.py

from typing import List
import logging
# from app.schemas.recommendation_schema import TopicRecommendation
from app.presentation.schemas.recommendation_schema import TopicRecommendation

logger = logging.getLogger(__name__)

PRIOR = 0.5
ALPHA = 3
MIN_COVERAGE = 0.3
PREREQ_THRESHOLD = 0.6
TOP_K = 5


class TopicRecommendationService:

    def __init__(self, repository):
        self.repository = repository

    def recommend_topics(self, user_id: int) -> List[TopicRecommendation]:

        mastery_count = self.repository.get_user_mastery_count(user_id)

        # 🔹 Cold Start
        if mastery_count == 0:
            foundational_topics = self.repository.get_foundational_topics()

            return [
                TopicRecommendation(
                    topic_id=t.id,
                    topic_name=t.name,
                    topic_mastery=0.0,
                    coverage=0.0,
                    weakness_score=0.0,
                    reason="cold_start",
                )
                for t in foundational_topics[:TOP_K]
            ]

        aggregates = self.repository.get_topic_mastery_aggregates(user_id)

        recommendations = []

        for agg in aggregates:

            if agg.total_concepts == 0:
                continue

            coverage = agg.known_concepts / agg.total_concepts

            if coverage < MIN_COVERAGE:
                continue

            topic_mastery = (agg.sum_mastery + ALPHA * PRIOR) / (
                agg.known_concepts + ALPHA
            )

            if not self.repository.prerequisites_satisfied(
                user_id=user_id, topic_id=agg.topic_id, threshold=PREREQ_THRESHOLD
            ):
                continue

            weakness_score = (1 - topic_mastery) * coverage

            recommendations.append(
                TopicRecommendation(
                    topic_id=agg.topic_id,
                    topic_name=agg.topic_name,
                    topic_mastery=round(topic_mastery, 3),
                    coverage=round(coverage, 3),
                    weakness_score=round(weakness_score, 3),
                    reason="weak_topic",
                )
            )

        # 🔹 Deterministic sorting
        recommendations.sort(
            key=lambda x: (
                x.weakness_score,  # primary
                -x.coverage,  # tie breaker (more data = higher priority)
            ),
            reverse=True,
        )

        return recommendations[:TOP_K]
