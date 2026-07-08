import os

from app.agents.openai_compatible_provider import OpenAICompatibleAgentProvider
from app.config import OPENAI_MODEL


class OpenAIAgentProvider(OpenAICompatibleAgentProvider):
    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required when AGENT_PROVIDER=openai")

    @property
    def model(self) -> str:
        return OPENAI_MODEL

    def _client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.api_key)
