from app.agents.base import AgentProvider
from app.agents.mock_provider import MockAgentProvider
from app.config import AGENT_PROVIDER


def get_agent_provider(name: str | None = None) -> AgentProvider:
    provider_name = (name or AGENT_PROVIDER).lower()
    if provider_name == "openai":
        from app.agents.openai_provider import OpenAIAgentProvider

        return OpenAIAgentProvider()
    if provider_name == "deepseek":
        from app.agents.deepseek_provider import DeepSeekAgentProvider

        return DeepSeekAgentProvider()
    if provider_name in {"qwen", "aliyun", "dashscope"}:
        from app.agents.qwen_provider import QwenAgentProvider

        return QwenAgentProvider()
    return MockAgentProvider()
