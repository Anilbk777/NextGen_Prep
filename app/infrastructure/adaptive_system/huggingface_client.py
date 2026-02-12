import logging
from typing import Optional, Dict

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import SystemMessage, HumanMessage

from .llm_client import LLMClient

logger = logging.getLogger(__name__)

class HuggingFaceChatClient(LLMClient):
    def __init__(
        self,
        *,
        repo_id: str,
        task: str = "text-generation",
        max_new_tokens: int = 512,
        do_sample: bool = False,
        repetition_penalty: float = 1.03,
        timeout: int = 30,
        huggingfacehub_api_token: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        endpoint_kwargs: Dict = {
            "repo_id": repo_id,
            "task": task,
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "repetition_penalty": repetition_penalty,
            "timeout": timeout,
        }

        if huggingfacehub_api_token:
            endpoint_kwargs["huggingfacehub_api_token"] = huggingfacehub_api_token
        if base_url:
            endpoint_kwargs["base_url"] = base_url

        llm = HuggingFaceEndpoint(**endpoint_kwargs)
        self._chat = ChatHuggingFace(llm=llm)

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        logger.debug("Generating via HuggingFace LLM")

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        result = self._chat.invoke(messages)
        print("*********************************************************************")
        print(str(result.content))
        print("*********************************************************************")
        return str(result.content)
