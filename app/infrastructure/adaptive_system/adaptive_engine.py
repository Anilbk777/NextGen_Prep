from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from sqlalchemy.exc import IntegrityError
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
    user_id: int
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
        logger.info(f"Starting learning session for user_id={user_id}, subject_id={subject_id}, topic_id={topic_id}")
        session = self._sessions.create_session(user_id, subject_id, topic_id)
        logger.info(f"Created session_id={session.session_id} for user_id={user_id}")
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
        logger.info(f"Getting next question for user_id={user_id}, topic_id={topic_id}")
        
        logger.debug(f"Building user state for user_id={user_id}")
        user_state = self._build_user_state(user_id, topic_id)
        logger.debug(f"User state built: ability={user_state.global_ability:.2f}, recent_accuracy={user_state.recent_accuracy:.2f}")

        # 1. Selection
        templates = self._questions.get_candidate_templates(topic_id)
        if not templates:
            logger.error(f"No templates found for topic_id={topic_id}")
            raise ValueError(f"No templates found for topic {topic_id}")

        # Personalization pre-filter:
        # restrict candidates to concepts in the learner's current ZPD
        filtered_templates = self._filter_templates_for_user(templates, user_state)
        logger.info(f"Filtered templates: {len(templates)} candidates → {len(filtered_templates)} after ZPD filtering")

        selected_template = self._bandit.select_template(
            templates=filtered_templates,
            user_context=user_state.__dict__,
            bandit_stats=self._responses.get_bandit_stats(user_id),
        )
        logger.info(f"Selected template_id={selected_template.template_id}, concept_id={selected_template.concept_id}, difficulty={selected_template.target_difficulty}")

        # 2. Generation / Retrieval (can be personalized using user_state)
        question_data = self._get_or_generate_question(selected_template, user_state)

        # Try to find an active session
        active_session = self._sessions.get_active_session(user_id, topic_id)
        session_id = active_session.session_id if active_session else None
        logger.info(f"Question ready: question_id={question_data.get('question_id')}, session_id={session_id}")

        return {
            "question_id": question_data.get("question_id"),
            "template_id": selected_template.template_id,
            "concept_id": selected_template.concept_id,
            "question_text": question_data["question_text"],
            "options": question_data["options"],
            "correct_option": question_data.get("correct_option"),
            "explanation": question_data.get("explanation"),
            "difficulty": selected_template.target_difficulty,
            "learning_objective": selected_template.learning_objective,
            "session_id": session_id,
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
        logger.info(f"Processing response for user_id={user_id}, question_id={question_id}, session_id={session_id}")
        
        question = self._get_question_model(question_id, template_id)
        if not question:
            logger.error(f"Question not found: question_id={question_id}")
            raise ValueError(f"Question {question_id} not found")

        correct = selected_option_index == question.correct_option
        logger.info(f"Response evaluated: correct={correct}, selected_option={selected_option_index}, correct_option={question.correct_option}")
        
        # 1. Detect Misconceptions
        misconception = None
        if not correct:
            misconception = self._detect_misconception(template_id, selected_option_index)
            if misconception:
                logger.info(f"Misconception detected: {misconception} for user_id={user_id}")

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
        try:
            self._responses.store_response(response_model)
            logger.debug(f"Response stored for user_id={user_id}, question_id={question_id}")
        except IntegrityError:
            # Handle duplicate submissions gracefully
            self._responses.db.rollback()
            existing = self._responses.get_response(user_id, question_id)
            if existing:
                # If it already exists, use the existing correctness for the rest of the flow
                correct = existing.correct
                logger.info(f"Duplicate response ignored for user_id={user_id}, question_id={question_id}")
            else:
                # If for some reason we can't find it, re-raise
                raise

        # 3. Update Session Metrics
        if session_id:
            self._sessions.update_session_metrics(session_id, correct)
            logger.debug(f"Session metrics updated for session_id={session_id}")

        # 4. Update Models
        new_theta = self._update_ability(user_id, question, correct)
        new_mastery = self._update_mastery(user_id, concept_id, correct)
        logger.info(f"Models updated for user_id={user_id}: new_ability={new_theta:.3f}, new_mastery={new_mastery:.3f} (concept_id={concept_id})")

        
        # 5. Update Bandit
        difficulty = question.template.target_difficulty if question.template and question.template.target_difficulty is not None else 0.5
        reward = self._calculate_reward(correct, response_time, difficulty)
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
        logger.debug(f"Bandit updated for template_id={template_id}, reward={reward:.3f}")

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
        logger.info(f"Ending learning session: session_id={session_id}")
        session = self._sessions.end_session(session_id)
        if not session:
            logger.error(f"Session not found: session_id={session_id}")
            raise ValueError(f"Session {session_id} not found")
        
        logger.info(f"Session ended: session_id={session_id}, attempted={session.questions_attempted}, correct={session.questions_correct}")
        return {
            "session_id": session.session_id,
            "subject_id": session.subject_id,
            "topic_id": session.topic_id,
            "questions_attempted": session.questions_attempted,
            "questions_correct": session.questions_correct,
            "start_time": session.start_time,
            "end_time": session.end_time,
        }

    # ---------------------------
    # Internal Logic
    # ---------------------------

    def _build_user_state(self, user_id: int, topic_id: int) -> UserState:
        recent = self._responses.get_recent_responses(user_id, limit=20)
        accuracy = sum(r.correct for r in recent) / len(recent) if recent else 0.5
        avg_time = np.mean([r.response_time for r in recent]) if recent else 30.0

        return UserState(
            user_id=user_id,
            global_ability=self._users.get_global_ability(user_id),
            recent_accuracy=accuracy,
            response_time_avg=avg_time,
            concept_mastery=self._users.get_concept_mastery(user_id),
            topic_id=topic_id
        )
    
    def _filter_templates_for_user(
        self,
        templates,
        user_state: UserState,
        *,
        min_mastery: float = 0.2,
        max_mastery: float = 0.95,
    ):
        """
        Restrict candidate templates to those whose concept mastery is within a
        reasonable band for the current learner.

        - Below min_mastery → likely too hard for now
        - Above max_mastery → concept already mastered; de-prioritize

        If filtering would remove all templates, we fall back to the original list
        to avoid dead-ends and still allow the bandit to explore.
        """
        mastery_map = user_state.concept_mastery or {}
        candidates = []

        logger.info(f"Filtering {len(templates)} templates with ZPD range: [{min_mastery}, {max_mastery}]")
        
        for template in templates:
            concept_id = getattr(template, "concept_id", None)
            mastery = mastery_map.get(concept_id, 0.5)
            
            if min_mastery <= mastery <= max_mastery:
                candidates.append(template)
                logger.debug(
                    f"✓ Included template_id={template.template_id}, concept_id={concept_id}, "
                    f"mastery={mastery:.3f} (within ZPD)"
                )
            else:
                logger.info(
                    f"✗ Excluded template_id={template.template_id}, concept_id={concept_id}, "
                    f"mastery={mastery:.3f} ({'too low' if mastery < min_mastery else 'already mastered'})"
                )

        if not candidates:
            logger.warning(
                f"ZPD filtering removed ALL templates! Falling back to original {len(templates)} templates. "
                f"This likely means: (1) only 1 topic available, or (2) all concepts mastered/not-started"
            )
            return templates
        
        logger.info(f"ZPD filtering kept {len(candidates)} out of {len(templates)} templates")
        return candidates

    def _get_or_generate_question(self, template, user_state: Optional[UserState] = None) -> Dict:
        """
        Fetch from cache or call LLM
        """
        logger.debug(f"Getting or generating question for template_id={template.template_id}")
        cached = None
        if user_state:
            cached = self._questions.get_unanswered_question(template.template_id, user_state.user_id)
        else:
            cached = self._questions.get_cached_question(template.template_id)

        if cached:
            logger.info(f"Using cached question_id={cached.question_id} for template_id={template.template_id}")
            return {
                "question_id": cached.question_id,
                "question_text": cached.question_text,
                "options": cached.options,
                "correct_option": cached.correct_option,
                "explanation": cached.explanation
            }

        if not self._question_gen:
            logger.error("No question generator available and no cached questions")
            raise ValueError("No question generator available and no cached questions")

        logger.info(f"Generating new question via LLM for template_id={template.template_id}, concept_id={template.concept_id}")
        concept = self._questions.get_concept(template.concept_id)
        try:
            generated = self._question_gen.generate_question(
                template=template,
                concept=concept,
                user_context=user_state.__dict__ if user_state is not None else None,
            )
            logger.info(f"LLM successfully generated question for template_id={template.template_id}")
            
            # Persist a minimal Question record; IRT parameters are derived
            # from the template when updating ability.
            new_q = Question(
                template_id=template.template_id,
                question_text=generated["question_text"],
                options=generated["options"],
                correct_option=generated["correct_option"],
                explanation=generated["explanation"],
            )
            saved = self._questions.save_question(new_q)
            logger.info(f"Saved generated question_id={saved.question_id} to database")
            return {
                "question_id": saved.question_id,
                "question_text": saved.question_text,
                "options": saved.options,
                "correct_option": saved.correct_option,
                "explanation": saved.explanation
            }
        except Exception as e:
            logger.error(f"LLM question generation failed for template_id={template.template_id}: {e}", exc_info=True)
            raise

    def _get_question_model(self, question_id: int, template_id: int) -> Optional[Question]:
        return self._questions.get_by_id(question_id)

    def _detect_misconception(self, template_id: int, selected_index: int) -> Optional[str]:
        template = self._questions.get_template(template_id)
        if not template or not template.misconception_patterns:
            return None
        
        # Simplified mapping: assumes index correlates to pattern list
        # Safely wrap around or check bounds? 
        # Given 3 distractors and N patterns, simple mapping isn't perfect but acceptable for MVP
        if selected_index < len(template.misconception_patterns):
            return template.misconception_patterns[selected_index]
        return None

    def _update_ability(self, user_id: int, question: Question, correct: bool) -> float:
        history = self._responses.get_irt_responses(user_id)
        current_ability = self._users.get_global_ability(user_id)

        # Derive IRT-like item parameters from the template instead of
        # non-existent Question columns.
        template = question.template
        base_difficulty = template.target_difficulty if template and template.target_difficulty is not None else 0.5
        # Map difficulty from [0,1] → roughly [-3,3] for theta space
        irt_difficulty = (base_difficulty - 0.5) * 6.0

        new_theta = self._irt.estimate_ability(
            responses=history + [{
                "correct": correct,
                "difficulty": irt_difficulty,
                "discrimination": 1.0,
                "guessing": 0.25,
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
