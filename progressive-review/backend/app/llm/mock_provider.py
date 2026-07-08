from app.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    def classify_document(self, input: dict) -> dict:
        return {"document_type": "educational_document", "confidence": 0.7}

    def summarize_section(self, input: dict) -> dict:
        text = " ".join(input.get("text", "").split())
        return {"summary": text[:260] + ("..." if len(text) > 260 else "")}

    def extract_claims(self, input: dict) -> dict:
        return {"claims": []}

    def generate_evidence_card(self, input: dict) -> dict:
        return {"evidence": input}

    def validate_claim_support(self, input: dict) -> dict:
        return {"supported": True, "confidence": 0.7}

