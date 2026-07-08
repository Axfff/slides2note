from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.models.review_ir import ReviewBlockStatus


WorkflowStage = Literal[
    "queued",
    "extracting",
    "segmenting",
    "planning",
    "generating_overview",
    "generating_blocks",
    "validating",
    "complete",
    "failed",
]


class WorkflowProgress(BaseModel):
    completed_blocks: int = 0
    total_blocks: int = 0


class WorkflowState(BaseModel):
    job_id: str
    status: str = "queued"
    stage: WorkflowStage = "queued"
    provider: str = "mock"
    progress: WorkflowProgress = Field(default_factory=WorkflowProgress)
    is_partial: bool = True
    current_block_id: str | None = None
    title: str | None = None
    page_count: int = 0
    claim_count: int = 0
    evidence_count: int = 0
    valid: bool | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    block_statuses: list[ReviewBlockStatus] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

