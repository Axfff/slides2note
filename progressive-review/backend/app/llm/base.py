from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def classify_document(self, input: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def summarize_section(self, input: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def extract_claims(self, input: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def generate_evidence_card(self, input: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def validate_claim_support(self, input: dict) -> dict:
        raise NotImplementedError

