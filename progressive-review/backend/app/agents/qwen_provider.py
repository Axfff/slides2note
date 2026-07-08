import os

from app.agents.openai_compatible_provider import OpenAICompatibleAgentProvider
from app.config import QWEN_BASE_URL, QWEN_MODEL


def normalize_qwen_model(model: str) -> str:
    aliases = {
        "qwen3.7max": "qwen3.7-max",
        "qwen37max": "qwen3.7-max",
    }
    return aliases.get(model.lower(), model)


class QwenAgentProvider(OpenAICompatibleAgentProvider):
    name = "qwen"

    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY or QWEN_API_KEY is required when AGENT_PROVIDER=qwen")

    @property
    def model(self) -> str:
        return normalize_qwen_model(QWEN_MODEL)

    def _client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, base_url=QWEN_BASE_URL)
