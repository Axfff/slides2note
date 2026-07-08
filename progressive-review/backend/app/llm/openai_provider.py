from app.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Placeholder for a future paid model implementation.

    The MVP intentionally uses MockLLMProvider so local runs do not require API keys.
    """

    def _not_enabled(self) -> dict:
        return {"error": "OpenAIProvider is not implemented in the MVP."}

    def classify_document(self, input: dict) -> dict:
        return self._not_enabled()

    def summarize_section(self, input: dict) -> dict:
        return self._not_enabled()

    def extract_claims(self, input: dict) -> dict:
        return self._not_enabled()

    def generate_evidence_card(self, input: dict) -> dict:
        return self._not_enabled()

    def validate_claim_support(self, input: dict) -> dict:
        return self._not_enabled()

