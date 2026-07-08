from abc import ABC, abstractmethod

from app.models.review_ir import AgentLayoutSpec, Claim, EvidenceCard, ReviewGenerationPlan, ReviewSection, ValidationResult, VisualInteractiveBlock
from app.models.source import ExtractedDocument


class AgentProvider(ABC):
    name: str

    @abstractmethod
    def plan_review(self, extracted: ExtractedDocument, outline: list[ReviewSection]) -> ReviewGenerationPlan:
        raise NotImplementedError

    @abstractmethod
    def generate_overview(self, extracted: ExtractedDocument, outline: list[ReviewSection]) -> ReviewSection:
        raise NotImplementedError

    @abstractmethod
    def generate_section_brief(self, section: ReviewSection, extracted: ExtractedDocument) -> ReviewSection:
        raise NotImplementedError

    @abstractmethod
    def generate_claims(self, section: ReviewSection, extracted: ExtractedDocument, start_index: int) -> list[Claim]:
        raise NotImplementedError

    @abstractmethod
    def generate_evidence_cards(self, claims: list[Claim], extracted: ExtractedDocument, start_index: int) -> list[EvidenceCard]:
        raise NotImplementedError

    @abstractmethod
    def validate_support(self, validation: ValidationResult) -> ValidationResult:
        raise NotImplementedError

    def build_layout_spec(
        self,
        extracted: ExtractedDocument,
        outline: list[ReviewSection],
        plan: ReviewGenerationPlan,
    ) -> AgentLayoutSpec:
        return AgentLayoutSpec()

    def generate_visual_blocks(
        self,
        extracted: ExtractedDocument,
        outline: list[ReviewSection],
    ) -> list[VisualInteractiveBlock]:
        return []
