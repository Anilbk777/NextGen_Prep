from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from ..db.models import Question, UserResponse
from .bandit import ContextualThompsonSampling
from .irt import ThreePLIRT
from .knowledge_tracing import BayesianKnowledgeTracing
from .question_generation import LLMQuestionGenerator
from ..repositories.question_repository import QuestionRepository
from ..repositories.response_repository import ResponseRepository
from ..repositories.learning_session_repository import LearningSessionRepository
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


# ---------------------------
# Domain Models
# ---------------------------

@dataclass
class UserState:
    global_ability: float
    recent_accuracy: float
    response_time_avg: float
    concept_mastery: Dict[int, float]
    topic_id: int


# ---------------------------
# Adaptive Engine
# ---------------------------

class AdaptiveLearningEngine:
    """
    Orchestrates adaptive learning decisions.
    Integrates IRT, KT, and Bandit systems.
    """

    def __init__(
        self,
        *,
        irt: ThreePLIRT,
        kt: BayesianKnowledgeTracing,
        bandit: ContextualThompsonSampling,
        question_generator: Optional[LLMQuestionGenerator],
        user_repo: UserRepository,
        question_repo: QuestionRepository,
        response_repo: ResponseRepository,
        session_repo: LearningSessionRepository,
    ):
        self._irt = irt
        self._kt = kt
        self._bandit = bandit
        self._question_gen = question_generator

        self._users = user_repo
        self._questions = question_repo
        self._responses = response_repo
        self._sessions = session_repo

    # ---------------------------
    # Public API
    # ---------------------------

    def start_session(self, user_id: int, subject_id: int, topic_id: int) -> Dict:
        """
        Starts a new learning session.
        """
        session = self._sessions.create_session(user_id, subject_id, topic_id)
        return {
            "session_id": session.session_id,
            "subject_id": session.subject_id,
            "topic_id": session.topic_id,
            "start_time": session.start_time.isoformat()
        }

    def get_next_question(self, user_id: int, topic_id: int) -> Dict:
        """
        Main adaptive loop: Select template → Generate/Fetch Question
        """
        user_state = self._build_user_state(user_id, topic_id)

        # 1. Selection
        templates = self._questions.get_candidate_templates(topic_id)
        if not templates:
            raise ValueError(f"No templates found for topic {topic_id}")

        selected_template = self._bandit.select_template(
            templates=templates,
            user_context=user_state.__dict__,
            bandit_stats=self._responses.get_bandit_stats(user_id),
        )

        # 2. Generation / Retrieval
        question_data = self._get_or_generate_question(selected_template)

        # Try to find an active session
        active_session = self._sessions.get_active_session(user_id, topic_id)

        return {
            "question_id": question_data.get("question_id"),
            "template_id": selected_template.template_id,
            "concept_id": selected_template.concept_id,
            "question_text": question_data["question_text"],
            "options": question_data["options"],
            "difficulty": selected_template.target_difficulty,
            "learning_objective": selected_template.learning_objective,
            "session_id": active_session.session_id if active_session else None,
            "metadata": {
                "generated": "question_id" not in question_data,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    def process_response(
        self,
        *,
        user_id: int,
        question_id: int,
        template_id: int,
        concept_id: int,
        selected_option_index: int,
        response_time: float,
        session_id: Optional[int] = None,
    ) -> Dict:
        """
        Update system state after user response.
        """
        question = self._get_question_model(question_id, template_id)
        if not question:
            raise ValueError(f"Question {question_id} not found")

        correct = selected_option_index == question.correct_option
        
        # 1. Detect Misconceptions
        misconception = None
        if not correct:
            misconception = self._detect_misconception(concept_id, selected_option_index)

        # 2. Store Response
        response_model = UserResponse(
            user_id=user_id,
            session_id=session_id,
            question_id=question_id,
            template_id=template_id,
            concept_id=concept_id,
            selected_option=selected_option_index,
            correct=correct,
            response_time=response_time,
            misconception_detected=misconception
        )
        self._responses.store_response(response_model)

        # 3. Update Session Metrics
        if session_id:
            self._sessions.update_session_metrics(session_id, correct)

        # 4. Update Models
        new_theta = self._update_ability(user_id, question, correct)
        new_mastery = self._update_mastery(user_id, concept_id, correct)
        
        # 5. Update Bandit
        reward = self._calculate_reward(correct, response_time, question.difficulty)
        stats = self._responses.get_bandit_stats(user_id)
        updated_bandit_params = self._bandit.update(
            template_id=template_id,
            reward=reward,
            current_stats=stats
        )
        self._responses.update_bandit_stats(
            user_id=user_id,
            template_id=template_id,
            alpha=updated_bandit_params["alpha"],
            beta=updated_bandit_params["beta"]
        )

        return {
            "correct": correct,
            "correct_option_index": question.correct_option,
            "explanation": question.explanation,
            "updated_mastery": new_mastery,
            "global_ability": new_theta,
            "misconception": misconception,
            "suggested_review": new_mastery < 0.7,
        }

    def end_session(self, session_id: int) -> Dict:
        """
        Ends a learning session.
        """
        session = self._sessions.end_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return {
            "session_id": session.session_id,
            "questions_attempted": session.questions_attempted,
            "questions_correct": session.questions_correct,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat()
        }

    # ---------------------------
    # Internal Logic
    # ---------------------------

    def _build_user_state(self, user_id: int, topic_id: int) -> UserState:
        recent = self._responses.get_recent_responses(user_id, limit=20)
        accuracy = sum(r.correct for r in recent) / len(recent) if recent else 0.5
        avg_time = np.mean([r.response_time for r in recent]) if recent else 30.0

        return UserState(
            global_ability=self._users.get_global_ability(user_id),
            recent_accuracy=accuracy,
            response_time_avg=avg_time,
            concept_mastery=self._users.get_concept_mastery(user_id),
            topic_id=topic_id
        )

    def _get_or_generate_question(self, template) -> Dict:
        """
        Fetch from cache or call LLM
        """
        cached = self._questions.get_cached_question(template.template_id)
        if cached:
            return {
                "question_id": cached.question_id,
                "question_text": cached.question_text,
                "options": cached.options,
                "correct_option": cached.correct_option,
                "explanation": cached.explanation
            }

        if not self._question_gen:
            raise ValueError("No question generator available and no cached questions")

        concept = self._questions.get_concept(template.concept_id)
        try:
            generated = self._question_gen.generate_question(
                template=template,
                concept=concept
            )
            new_q = Question(
                template_id=template.template_id,
                question_text=generated["question_text"],
                options=generated["options"],
                correct_option=generated["correct_option"],
                explanation=generated["explanation"],
                difficulty=template.target_difficulty,
                discrimination=1.0,
                guessing=0.25
            )
            saved = self._questions.save_question(new_q)
            return {
                "question_id": saved.question_id,
                "question_text": saved.question_text,
                "options": saved.options,
                "correct_option": saved.correct_option,
                "explanation": saved.explanation
            }
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    def _get_question_model(self, question_id: int, template_id: int) -> Optional[Question]:
        return self._questions.get_by_id(question_id)

    def _detect_misconception(self, concept_id: int, selected_index: int) -> Optional[str]:
        concept = self._questions.get_concept(concept_id)
        if not concept or not concept.common_misconceptions:
            return None
        
        if selected_index < len(concept.common_misconceptions):
            return concept.common_misconceptions[selected_index]
        return None

    def _update_ability(self, user_id: int, question: Question, correct: bool) -> float:
        history = self._responses.get_irt_responses(user_id)
        current_ability = self._users.get_global_ability(user_id)

        new_theta = self._irt.estimate_ability(
            responses=history + [{
                "correct": correct,
                "difficulty": question.difficulty,
                "discrimination": question.discrimination,
                "guessing": question.guessing,
            }],
            initial_theta=current_ability,
        )

        self._users.update_global_ability(user_id, new_theta)
        return new_theta

    def _update_mastery(self, user_id: int, concept_id: int, correct: bool) -> float:
        masteries = self._users.get_concept_mastery(user_id)
        current = masteries.get(concept_id, 0.3)
        
        updated = self._kt.update_mastery(current, correct)
        self._users.update_concept_mastery(user_id, concept_id, updated)

        prereqs = self._users.get_prerequisites(concept_id)
        if prereqs:
            prereq_masteries = {pid: masteries.get(pid, 0.5) for pid in prereqs}
            updated_prereqs = self._kt.propagate_to_prerequisites(prereq_masteries, correct)
            for pid, m in updated_prereqs.items():
                self._users.update_concept_mastery(user_id, pid, m)

        return updated

    def _calculate_reward(self, correct: bool, response_time: float, difficulty: float) -> float:
        base = 1.0 if correct else 0.0
        optimal_time = (difficulty * 60) + 15
        time_efficiency = max(0.0, 1.0 - abs(response_time - optimal_time) / optimal_time)
        return float(np.clip(0.7 * base + 0.3 * time_efficiency, 0.0, 1.0))
