from typing import Protocol

class LLMClient(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """
        Generates a response from the LLM based on system and user prompts.
        """
        ...
