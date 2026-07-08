from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.models.source import BBox, SourceFrame


ProgressiveLevel = Literal["overview", "brief", "standard", "evidence", "full"]
VisualBlockType = Literal[
    "hero",
    "visual_summary",
    "concept_grid",
    "callout",
    "comparison_table",
    "question_bank",
    "interactive_checklist",
    "source_timeline",
    "agent_slot",
]
VisualBlockPlacement = Literal["hero", "after_overview", "before_sections", "after_sections", "source_rail"]


class SourceRef(BaseModel):
    source_frame_id: str
    source_unit_id: str | None = None
    page_index: int | None = None
    bbox: BBox | None = None
    quote: str | None = None


class Claim(BaseModel):
    claim_id: str
    text: str
    explanation: str | None = None
    source_refs: list[SourceRef]
    confidence: float = 0.75
    tags: list[str] = Field(default_factory=list)
    progressive_level: ProgressiveLevel = "standard"


class EvidenceCard(BaseModel):
    evidence_id: str
    claim_id: str
    title: str
    evidence_text: str
    why_it_matters: str
    caveat: str | None = None
    source_refs: list[SourceRef]


class ReviewSection(BaseModel):
    section_id: str
    title: str
    level: int
    summary: str
    source_frame_ids: list[str]
    children: list["ReviewSection"] = Field(default_factory=list)
    key_claim_ids: list[str] = Field(default_factory=list)
    full_notes: str | None = None


class AgentLayoutSlot(BaseModel):
    slot_id: str
    title: str
    placement: VisualBlockPlacement
    allowed_block_types: list[VisualBlockType] = Field(default_factory=list)
    source_frame_ids: list[str] = Field(default_factory=list)
    description: str | None = None
    agent_editable: bool = True


class AgentLayoutSpec(BaseModel):
    mode: Literal["default", "agent_composed"] = "default"
    density: Literal["compact", "comfortable"] = "comfortable"
    style_preset: Literal["workspace", "cheatsheet"] = "workspace"
    reading_width_px: int = 1180
    review_column_min_px: int = 420
    source_column_min_px: int = 360
    slots: list[AgentLayoutSlot] = Field(default_factory=list)
    quality_targets: list[str] = Field(default_factory=list)
    notes: str | None = None


class VisualInteractiveBlock(BaseModel):
    block_id: str
    type: VisualBlockType
    title: str
    placement: VisualBlockPlacement
    source_refs: list[SourceRef] = Field(default_factory=list)
    payload: dict = Field(default_factory=dict)
    status: Literal["queued", "running", "complete", "failed"] = "complete"


class ValidationResult(BaseModel):
    valid: bool = True
    warnings: list[str] = Field(default_factory=list)


class ReviewGenerationPlan(BaseModel):
    provider: str
    block_ids: list[str] = Field(default_factory=list)
    strategy: str = "overview_first_auto_blocks"
    layout_strategy: str = "source_linked_cheatsheet"
    quality_targets: list[str] = Field(default_factory=list)
    allowed_visual_block_types: list[VisualBlockType] = Field(default_factory=list)


class ReviewBlockStatus(BaseModel):
    block_id: str
    type: str
    title: str
    status: Literal["queued", "running", "complete", "failed"] = "queued"
    source_frame_ids: list[str] = Field(default_factory=list)
    error: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProgressiveReviewIR(BaseModel):
    document_id: str
    title: str
    document_type: str
    source_frames: list[SourceFrame]
    outline: list[ReviewSection]
    claims: list[Claim]
    evidence_cards: list[EvidenceCard]
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pipeline_version: str
    validation: ValidationResult | None = None
    is_partial: bool = False
    generation_plan: ReviewGenerationPlan | None = None
    block_statuses: list[ReviewBlockStatus] = Field(default_factory=list)
    layout_spec: AgentLayoutSpec | None = None
    visual_blocks: list[VisualInteractiveBlock] = Field(default_factory=list)


ReviewSection.model_rebuild()
