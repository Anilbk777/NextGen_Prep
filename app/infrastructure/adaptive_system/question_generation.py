# core/question_generation.py

from __future__ import annotations

import json
import logging
from typing import Dict, List, Protocol

from tenacity import retry, stop_after_attempt, wait_exponential

import openai


logger = logging.getLogger(__name__)


# ---------------------------
# LLM Client Abstraction
# ---------------------------

class LLMClient(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        ...


class OpenAIChatClient:
    """
    Concrete OpenAI ChatCompletion client.
    Easily replaceable with Azure OpenAI / Anthropic / local LLM.
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout: int = 30,
    ):
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout=self._timeout,
        )

        return response.choices[0].message.content


# ---------------------------
# Question Generator
# ---------------------------

class LLMQuestionGenerator:
    """
    Domain service responsible for generating MCQs using an LLM.
    """

    SYSTEM_PROMPT = "You are an expert educational content creator."

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_question(self, template: any, concept: any) -> Dict:
        prompt = self._build_prompt(template, concept)

        try:
            raw_output = self._llm.generate(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=prompt,
            )

            return self._parse_response(
                raw_output=raw_output,
                template=template,
                concept=concept,
            )

        except Exception:
            logger.exception(
                "LLM question generation failed",
                extra={
                    "template_id": getattr(template, 'template_id', None),
                    "concept_id": getattr(concept, 'concept_id', None),
                },
            )
            return self._fallback_question(template, concept)

    # ---------------------------
    # Prompt Construction
    # ---------------------------

    def _build_prompt(self, template: any, concept: any) -> str:
        misconceptions = concept.common_misconceptions if concept else []
        misconceptions_text = "\n".join(f"- {m}" for m in misconceptions)

        return f"""
Generate a multiple-choice question.

Learning Objective: {template.learning_objective}
Concept: {concept.name}
Description: {concept.description}
Difficulty (1–5): {template.target_difficulty}
Question Style: {template.question_style}

Common Misconceptions:
{misconceptions_text or "None"}

Requirements:
1. Clear question stem
2. Exactly 4 options
3. One correct option
4. Detailed explanation
5. Distractors should reflect misconceptions

Respond ONLY in valid JSON:
{{
  "question_text": "string",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct_option": 0,
  "explanation": "string"
}}
""".strip()

    # ---------------------------
    # Response Parsing & Validation
    # ---------------------------

    def _parse_response(
        self,
        *,
        raw_output: str,
        template: any,
        concept: any,
    ) -> Dict:
        try:
            json_payload = self._extract_json(raw_output)
            data = json.loads(json_payload)

            self._validate_question_schema(data)

            return {
                "question_text": data["question_text"],
                "options": data["options"],
                "correct_option": data["correct_option"],
                "explanation": data["explanation"],
                "template_id": template.template_id,
                "concept_id": concept.concept_id,
            }

        except Exception as exc:
            logger.warning(
                "Invalid LLM response format",
                extra={"error": str(exc), "raw_output": raw_output},
            )
            raise

    @staticmethod
    def _extract_json(text: str) -> str:
        if "```" in text:
            return text.split("```")[1].replace("json", "").strip()
        return text.strip()

    @staticmethod
    def _validate_question_schema(data: Dict) -> None:
        required_keys = {"question_text", "options", "correct_option", "explanation"}

        if not required_keys.issubset(data):
            raise ValueError("Missing required keys")

        if not isinstance(data["options"], list) or len(data["options"]) != 4:
            raise ValueError("Exactly 4 options required")

        if not isinstance(data["correct_option"], int) or not 0 <= data["correct_option"] <= 3:
            raise ValueError("correct_option must be between 0 and 3")

    # ---------------------------
    # Fallback
    # ---------------------------

    @staticmethod
    def _fallback_question(template: any, concept: any) -> Dict:
        return {
            "question_text": f"What best describes {concept.name}?",
            "options": [
                f"A. A core concept related to the current topic",
                f"B. An unrelated concept",
                f"C. The opposite of {concept.name}",
                f"D. A deprecated idea",
            ],
            "correct_option": 0,
            "explanation": "Fallback question due to generation failure.",
            "template_id": template.template_id,
            "concept_id": concept.concept_id,
        }
