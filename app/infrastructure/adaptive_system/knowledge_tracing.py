# core/knowledge_tracing.py

from __future__ import annotations
import logging
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


# =========================================================
# 1. Bayesian Knowledge Tracing (ONLINE / REAL-TIME)
# =========================================================

class BayesianKnowledgeTracing:
    """
    Stateless Bayesian Knowledge Tracing (BKT).

    This class does NOT store user state internally.
    Mastery must be fetched from and persisted to the database.
    """

    def __init__(
        self,
        p_init: float = 0.3,
        p_learn: float = 0.2,
        p_guess: float = 0.1,
        p_slip: float = 0.1,
    ):
        self._validate_params(p_init, p_learn, p_guess, p_slip)

        self.p_init = p_init
        self.p_learn = p_learn
        self.p_guess = p_guess
        self.p_slip = p_slip

    @staticmethod
    def _validate_params(*params: float) -> None:
        for p in params:
            if not 0.0 <= p <= 1.0:
                raise ValueError("BKT parameters must be between 0 and 1")

    def update_mastery(self, mastery: float, correct: bool) -> float:
        """
        Update concept mastery after a single response.

        Args:
            mastery: Current mastery probability (0–1)
            correct: Whether the response was correct

        Returns:
            Updated mastery probability (0–1)
        """

        mastery = float(np.clip(mastery, 0.0, 1.0))

        # Likelihoods
        p_correct = (
            mastery * (1 - self.p_slip)
            + (1 - mastery) * self.p_guess
        )

        p_incorrect = 1.0 - p_correct

        # Posterior belief
        if correct:
            if p_correct == 0:
                logger.warning("p_correct is zero; returning prior mastery")
                posterior = mastery
            else:
                posterior = (mastery * (1 - self.p_slip)) / p_correct
        else:
            if p_incorrect == 0:
                logger.warning("p_incorrect is zero; returning prior mastery")
                posterior = mastery
            else:
                posterior = (mastery * self.p_slip) / p_incorrect

        # Learning transition
        updated_mastery = posterior + (1 - posterior) * self.p_learn

        updated_mastery = float(np.clip(updated_mastery, 0.0, 1.0))

        logger.debug(
            "BKT update | before=%.4f correct=%s after=%.4f",
            mastery,
            correct,
            updated_mastery,
        )

        return updated_mastery

    def propagate_to_prerequisites(self, prereq_masteries: Dict[int, float], correct: bool) -> Dict[int, float]:
        """
        Update prerequisite masteries based on performance on a dependent concept.
        Logic: If correct, increase prereq mastery slightly. If incorrect, decrease slightly.
        """
        updated = {}
        for pid, mastery in prereq_masteries.items():
            # If student got it right, boost prereqs with lower learning rate
            # If student got it wrong, penalize prereqs with lower penalty
            adjustment = 0.02 if correct else -0.05 
            updated[pid] = float(np.clip(mastery + adjustment, 0.0, 1.0))
        return updated


# =========================================================
# 2. Deep Knowledge Tracing (OFFLINE TRAINED / ONLINE INFER)
# =========================================================

class DeepKnowledgeTracing:
    """
    LSTM-based Deep Knowledge Tracing (DKT).

    Intended usage:
    - Train OFFLINE on historical sequences
    - Load trained model for ONLINE inference
    """

    def __init__(
        self,
        num_concepts: int,
        embedding_dim: int = 32,
        hidden_dim: int = 64,
        device: Optional[str] = None,
    ):
        import torch
        import torch.nn as nn

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.embedding = nn.Embedding(num_concepts, embedding_dim)
        self.lstm = nn.LSTM(
            input_size=embedding_dim + 1,  # + correctness signal
            hidden_size=hidden_dim,
            batch_first=True,
        )
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

        self.model = nn.ModuleDict({
            "embedding": self.embedding,
            "lstm": self.lstm,
            "fc": self.fc,
            "sigmoid": self.sigmoid,
        }).to(self.device)

        self.loss_fn = nn.BCELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

    # -----------------------------
    # Training (offline)
    # -----------------------------

    def train(
        self,
        sequences: List[List[Dict]],
        epochs: int = 10,
        batch_size: int = 32,
    ) -> None:
        """
        Train DKT on user interaction sequences.

        Each interaction must include:
        - concept_id (int)
        - correct (0 or 1)
        """

        import torch

        self.model.train()

        for epoch in range(epochs):
            losses = []

            for seq in sequences:
                concepts = torch.tensor(
                    [x["concept_id"] for x in seq],
                    dtype=torch.long,
                    device=self.device,
                )
                correctness = torch.tensor(
                    [x["correct"] for x in seq],
                    dtype=torch.float32,
                    device=self.device,
                ).unsqueeze(-1)

                emb = self.embedding(concepts)
                x = torch.cat([emb, correctness], dim=-1)

                outputs, _ = self.lstm(x)
                preds = self.sigmoid(self.fc(outputs)).squeeze(-1)

                loss = self.loss_fn(preds[:-1], correctness[1:].squeeze())
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

                losses.append(loss.item())

            logger.info(
                "DKT epoch %d | loss=%.4f",
                epoch + 1,
                float(np.mean(losses)),
            )

    # -----------------------------
    # Inference (online)
    # -----------------------------

    def predict_mastery(self, sequence: List[Dict]) -> float:
        """
        Predict mastery probability from a sequence of interactions.
        """

        import torch

        self.model.eval()

        with torch.no_grad():
            concepts = torch.tensor(
                [x["concept_id"] for x in sequence],
                dtype=torch.long,
                device=self.device,
            )
            correctness = torch.tensor(
                [x["correct"] for x in sequence],
                dtype=torch.float32,
                device=self.device,
            ).unsqueeze(-1)

            emb = self.embedding(concepts)
            x = torch.cat([emb, correctness], dim=-1)

            outputs, _ = self.lstm(x)
            mastery = self.sigmoid(self.fc(outputs[-1])).item()

        return float(np.clip(mastery, 0.0, 1.0))
