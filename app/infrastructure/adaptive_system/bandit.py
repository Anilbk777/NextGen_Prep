# core/bandit.py

from __future__ import annotations
import logging
from typing import Dict, List
import numpy as np

logger = logging.getLogger(__name__)


# =========================================================
# Contextual Thompson Sampling Bandit
# =========================================================

class ContextualThompsonSampling:
    """
    Stateless Contextual Thompson Sampling.

    - Alpha/Beta are persisted in DB (BanditStats table)
    - Context affects selection but does NOT overwrite uncertainty
    """

    def __init__(
        self,
        context_weight: float = 0.25,
        alpha_prior: float = 1.0,
        beta_prior: float = 1.0,
    ):
        self.context_weight = context_weight
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior

    # -----------------------------------------------------
    # Template Selection
    # -----------------------------------------------------

    def select_template(
        self,
        templates: List[any],  # List of Template objects
        user_context: Dict,
        bandit_stats: Dict[int, Dict],
    ) -> any:
        """
        Select the next template using Contextual Thompson Sampling.

        Args:
            templates: candidate templates (models.Template)
            user_context: {
                global_ability,
                concept_mastery,
                recent_accuracy,
                avg_response_time
            }
            bandit_stats: {template_id: {alpha, beta}}

        Returns:
            Selected template object
        """

        if not templates:
            raise ValueError("No templates available for selection")

        scored_templates = []

        for template in templates:
            template_id = template.template_id

            stats = bandit_stats.get(template_id, {})
            alpha = stats.get("alpha", self.alpha_prior)
            beta = stats.get("beta", self.beta_prior)

            # Thompson Sampling
            sampled_reward = np.random.beta(alpha, beta)

            # Context alignment score (0–1)
            context_score = self._context_score(template, user_context)

            # Final score
            final_score = sampled_reward + self.context_weight * context_score

            scored_templates.append((final_score, template))

        selected = max(scored_templates, key=lambda x: x[0])[1]

        logger.debug(
            "Bandit selected template=%s",
            selected.template_id,
        )

        return selected

    # -----------------------------------------------------
    # Context Scoring
    # -----------------------------------------------------

    def _context_score(self, template: any, user_context: Dict) -> float:
        """
        Computes how well a template fits the user's current learning state.

        Output range: [0, 1]
        """

        score = 0.0
        weight_sum = 0.0

        # ---- Difficulty vs Ability (IRT-aware) ----
        theta = user_context.get("global_ability", 0.0)  # ~[-3, 3]
        target_diff = template.target_difficulty  # 0–1 scale

        # Map θ (range roughly -3 to 3) to 0-1 scale
        normalized_theta = (theta + 3) / 6
        normalized_theta = max(0.0, min(1.0, normalized_theta))
        
        diff_alignment = 1.0 - abs(target_diff - normalized_theta)

        score += 0.4 * diff_alignment
        weight_sum += 0.4

        # ---- Concept Mastery (Zone of Proximal Development) ----
        mastery_map = user_context.get("concept_mastery", {})
        mastery = mastery_map.get(template.concept_id, 0.5)

        mastery_alignment = 1.0 - abs(mastery - 0.7)  # peak at 70%
        mastery_alignment = max(0.0, mastery_alignment)

        score += 0.4 * mastery_alignment
        weight_sum += 0.4

        # ---- Recent Accuracy Stabilization ----
        recent_accuracy = user_context.get("recent_accuracy", 0.7)

        if recent_accuracy < 0.3 and target_diff <= 0.4:
            score += 0.2
            weight_sum += 0.2
        elif recent_accuracy > 0.9 and target_diff >= 0.7:
            score += 0.2
            weight_sum += 0.2

        if weight_sum == 0:
            return 0.0

        return float(np.clip(score / weight_sum, 0.0, 1.0))

    # -----------------------------------------------------
    # Parameter Update
    # -----------------------------------------------------

    def update(
        self,
        template_id: int,
        reward: float,
        current_stats: Dict[int, Dict],
    ) -> Dict:
        """
        Update alpha/beta after observing reward.

        Reward semantics:
        - 1.0 → strong learning signal
        - 0.0 → no learning / failure
        - fractional → partial learning gain
        """

        reward = float(np.clip(reward, 0.0, 1.0))

        stats = current_stats.get(template_id, {})
        alpha = stats.get("alpha", self.alpha_prior)
        beta = stats.get("beta", self.beta_prior)

        alpha += reward
        beta += 1.0 - reward

        # Safety bounds
        alpha = float(np.clip(alpha, 1.0, 100.0))
        beta = float(np.clip(beta, 1.0, 100.0))

        logger.debug(
            "Bandit update | template=%s alpha=%.2f beta=%.2f reward=%.2f",
            template_id,
            alpha,
            beta,
            reward,
        )

        return {"alpha": alpha, "beta": beta}
