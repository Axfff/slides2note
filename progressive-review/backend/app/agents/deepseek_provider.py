import os

from app.agents.openai_compatible_provider import OpenAICompatibleAgentProvider
from app.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class DeepSeekAgentProvider(OpenAICompatibleAgentProvider):
    name = "deepseek"

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required when AGENT_PROVIDER=deepseek")

    @property
    def model(self) -> str:
        return DEEPSEEK_MODEL

    def _client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, base_url=DEEPSEEK_BASE_URL)
