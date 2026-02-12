# question_generation.py

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential



from .llm_client import LLMClient


logger = logging.getLogger(__name__)


# LLM Question Generator

class LLMQuestionGenerator:
    """
    Domain service responsible for generating MCQs using an LLM.
    """

    SYSTEM_PROMPT = "You are an expert educational content creator."

    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def generate_question(
        self,
        template: any,
        concept: any,
        user_context: Optional[Dict] = None,
    ) -> Dict:
        logger.info(
            f"Starting question generation for template_id={template.template_id}, "
            f"concept_id={concept.concept_id}"
        )
        
        prompt = self._build_prompt(template, concept, user_context=user_context)
        logger.debug(f"Built prompt for template_id={template.template_id}, length={len(prompt)} chars")

        raw_output = self._llm.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
        )
        logger.debug(f"LLM response received, length={len(raw_output)} chars")

        return self._parse_response(
            raw_output=raw_output,
            template=template,
            concept=concept,
        )

    # ---------------------------
    # Prompt Construction
    # ---------------------------

    def _build_prompt(
        self,
        template: any,
        concept: any,
        user_context: Optional[Dict] = None,
    ) -> str:
        """
        Build optimized LLM prompt for high-quality MCQ generation.
        """
        # Build misconception list with clear formatting
        misconceptions = template.misconception_patterns if template.misconception_patterns else []
        misconceptions_text = "\n".join(f"{i+1}. {m}" for i, m in enumerate(misconceptions))

        # Build adaptive difficulty guidance
        personalization_block = ""
        if user_context:
            ability = user_context.get("global_ability", 0.0)
            recent_accuracy = user_context.get("recent_accuracy", 0.7)
            response_time_avg = user_context.get("response_time_avg", 30.0)

            # Determine difficulty tier
            if ability < -1.0 or recent_accuracy < 0.5:
                tier = "BEGINNER"
                guidance = "Use simple language, direct questions, and obvious distractors. Avoid trick wording."
            elif ability > 1.0 and recent_accuracy > 0.8:
                tier = "ADVANCED"
                guidance = "Use sophisticated scenarios, subtle distractors, and require multi-step reasoning."
            else:
                tier = "INTERMEDIATE"
                guidance = "Balance clarity with challenge. Include plausible but clearly incorrect distractors."

            personalization_block = f"""
STUDENT ADAPTATION ({tier}):
- Current ability: {ability:.2f} (range: -3 to +3)
- Recent accuracy: {recent_accuracy:.0%}
- Avg response time: {response_time_avg:.1f}s
→ {guidance}
"""

        return f"""You are an expert educational assessment designer. Generate a high-quality multiple-choice question.

CONCEPT INFORMATION:
Name: {concept.name}
Description: {concept.description}

ASSESSMENT OBJECTIVES:
Intent: {template.intent or "Test understanding of the concept"}
Learning Objective: {template.learning_objective}
Target Difficulty: {template.target_difficulty:.2f} (0=easy, 1=hard)
Question Style: {template.question_style}

CORRECT ANSWER CRITERIA:
{template.correct_reasoning or "Student demonstrates accurate understanding of the concept"}

COMMON MISCONCEPTIONS TO ADDRESS:
{misconceptions_text if misconceptions_text else "None specified - create plausible distractors based on concept"}

{personalization_block.strip()}

QUESTION REQUIREMENTS:
✓ Write a clear, unambiguous question stem
✓ Create exactly 4 answer options (A, B, C, D)
✓ ONE correct answer that aligns with correct reasoning criteria
✓ THREE distractors that:
  - Are plausible and tempting to students who have misconceptions
  - Map to the misconception patterns listed above (when provided)
  - Are similar in length and complexity to the correct answer
  - Don't include "all of the above" or "none of the above"
✓ Provide a detailed explanation that:
  - Explains why the correct answer is right
  - Addresses why each distractor is incorrect
  - Connects to the underlying concept

OUTPUT FORMAT (CRITICAL - must be valid JSON with EXACTLY this structure):
{{
  "question_text": "Clear, specific question stem",
  "options": [
    "Option A text (do NOT include A), B), C), D) prefixes)",
    "Option B text",
    "Option C text",
    "Option D text"
  ],
  "correct_option": 0,
  "explanation": "Concise explanation (2-3 sentences max) covering why the correct answer is right. Keep it brief."
}}

IMPORTANT: 
- Do NOT add A), B), C), D) prefixes to options
- Do NOT use nested objects for "explanation" - it MUST be a simple string
- Do NOT use markdown bold (**text**) inside the JSON values
- Keep explanation BRIEF (2-3 sentences maximum) - do NOT explain every distractor in detail

Generate the question now:""".strip()

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
            logger.debug(f"Extracting JSON from LLM response for template_id={template.template_id}")
            json_payload = self._extract_json(raw_output)
            
            # Log the extracted payload for debugging
            if not json_payload or not json_payload.strip():
                logger.error(
                    f"Extracted JSON payload is empty for template_id={template.template_id}",
                    extra={"raw_output_preview": raw_output[:1000]}
                )
                raise ValueError("Failed to extract valid JSON from LLM response - response may be incomplete")
            
            logger.debug(f"Extracted JSON payload: {json_payload[:500]}...")
            
            # Try to parse JSON - if it fails due to control characters, try escaping them
            try:
                data = json.loads(json_payload)
            except json.JSONDecodeError as e:
                if "control character" in str(e) or "Invalid" in str(e):
                    logger.warning(f"JSON has control characters, attempting to escape them")
                    # Escape control characters that might be in string values
                    # This is a simple approach: replace literal newlines/tabs with escaped versions
                    # We do this character by character to preserve JSON structure
                    cleaned = []
                    in_string = False
                    escape_next = False
                    
                    for i, char in enumerate(json_payload):
                        if escape_next:
                            cleaned.append(char)
                            escape_next = False
                            continue
                            
                        if char == '\\':
                            cleaned.append(char)
                            escape_next = True
                            continue
                            
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            cleaned.append(char)
                            continue
                        
                        # Only escape control chars when inside strings
                        if in_string:
                            if char == '\n':
                                cleaned.append('\\n')
                            elif char == '\r':
                                cleaned.append('\\r')
                            elif char == '\t':
                                cleaned.append('\\t')
                            else:
                                cleaned.append(char)
                        else:
                            cleaned.append(char)
                    
                    json_payload = ''.join(cleaned)
                    logger.debug(f"Cleaned JSON to escape control characters")
                    data = json.loads(json_payload)
                else:
                    # Log more details about the parsing error
                    logger.error(
                        f"JSON parsing failed: {str(e)}",
                        extra={
                            "error_type": type(e).__name__,
                            "json_preview": json_payload[:500]
                        }
                    )
                    raise
            
            logger.debug(f"Successfully parsed JSON for template_id={template.template_id}")

            self._validate_question_schema(data)
            logger.info(
                f"Question validated successfully for template_id={template.template_id}, "
                f"question length={len(data['question_text'])} chars"
            )

            # Clean options: remove A), B), C), D) prefixes and extra whitespace
            cleaned_options = []
            for opt in data["options"]:
                # Remove prefixes like "A)", "A:", "B)", etc.
                cleaned = re.sub(r'^[A-D][:\)]\s*', '', opt.strip())
                cleaned_options.append(cleaned)
            
            # Handle explanation being an object (LLM sometimes ignores format)
            explanation = data["explanation"]
            if isinstance(explanation, dict):
                logger.warning(f"LLM returned complex explanation object, converting to string")
                # Try to extract meaningful text from the object
                explanation = str(explanation.get("correct_answer_rationale", {}).get("explanation_text", "")) or str(explanation)

            return {
                "question_text": data["question_text"],
                "options": cleaned_options,
                "correct_option": data["correct_option"],
                "explanation": explanation,
                "template_id": template.template_id,
                "concept_id": concept.concept_id,
            }

        except json.JSONDecodeError as exc:
            logger.error(
                f"JSON parsing failed for template_id={template.template_id}: {exc}",
                extra={"error": str(exc), "raw_output_preview": raw_output[:500]}
            )
            raise
        except Exception as exc:
            logger.warning(
                f"Invalid LLM response format for template_id={template.template_id}",
                extra={"error": str(exc), "raw_output_preview": raw_output[:500]},
            )
            raise

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        Extract a JSON object from LLM output.

        Many models (including reasoning models) may emit extra prose or
        <think>...</think> blocks around the JSON. We try, in order:
        - fenced ```json ... ``` blocks
        - a raw JSON object covering the full string
        - the first {...} span we can find
        
        After extraction, we clean markdown formatting (bold, italic)
        and escape control characters that some LLMs add inside JSON values.
        """
        json_text = ""
        
        if "```" in text:
            # Handle ```json ... ``` or ``` ... ``` fences
            parts = text.split("```")
            # Take the first fenced block that looks like JSON
            for part in parts[1:]:
                cleaned = part.replace("json", "").strip()
                if cleaned.startswith("{") and "}" in cleaned:
                    json_text = cleaned
                    break

        if not json_text:
            stripped = text.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                json_text = stripped

        if not json_text:
            # Fallback: grab the first {...} span
            start = text.strip().find("{")
            end = text.strip().rfind("}")
            if start != -1 and end != -1 and end > start:
                json_text = text.strip()[start : end + 1]

        if not json_text:
            json_text = text.strip()
        
        # Clean markdown formatting from JSON values
        # Remove bold markers: **text** -> text
        json_text = json_text.replace("**", "")
        
        logger.debug(f"Cleaned JSON length: {len(json_text)} chars, first 300: {json_text[:300]}")
        
        return json_text

    @staticmethod
    def _validate_question_schema(data: Dict) -> None:
        required_keys = {"question_text", "options", "correct_option", "explanation"}

        if not required_keys.issubset(data):
            missing = required_keys - set(data.keys())
            logger.error(f"Missing required keys in generated question: {missing}")
            raise ValueError(f"Missing required keys: {missing}")

        if not isinstance(data["options"], list) or len(data["options"]) != 4:
            logger.error(f"Invalid options count: expected 4, got {len(data.get('options', []))}")
            raise ValueError("Exactly 4 options required")

        if not isinstance(data["correct_option"], int) or not 0 <= data["correct_option"] <= 3:
            logger.error(f"Invalid correct_option: {data.get('correct_option')}")
            raise ValueError("correct_option must be between 0 and 3")

