from datetime import datetime, timezone
from pathlib import Path

from app.agents.factory import get_agent_provider
from app.config import PIPELINE_VERSION
from app.models.review_ir import ProgressiveReviewIR, ReviewBlockStatus, ReviewSection
from app.models.workflow import WorkflowState
from app.services.pdf_extractor import PDFExtractor
from app.services.section_segmenter import SectionSegmenter
from app.services.validator import IRValidator
from app.storage.file_store import FileStore


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentWorkflowRunner:
    def __init__(self, store: FileStore | None = None):
        self.store = store or FileStore()
        self.extractor = PDFExtractor()
        self.segmenter = SectionSegmenter()
        self.validator = IRValidator()

    def initialize_queued_job(self, job_id: str, provider_name: str = "mock") -> WorkflowState:
        state = WorkflowState(job_id=job_id, provider=provider_name)
        self._write_state(state)
        return state

    def run(self, job_id: str, pdf_path: Path, provider_name: str | None = None) -> ProgressiveReviewIR:
        state = self._read_or_create_state(job_id, provider_name)
        provider = get_agent_provider(provider_name or state.provider)
        state.provider = provider.name

        ir: ProgressiveReviewIR | None = None
        try:
            self._set_stage(state, "extracting")
            extracted = self.extractor.extract(pdf_path, self.store.pages_dir(job_id), document_id=job_id)
            self.store.write_json(job_id, "source_frames.json", extracted.model_dump(mode="json"))
            state.title = extracted.title
            state.page_count = len(extracted.source_frames)
            self._write_state(state)

            self._set_stage(state, "segmenting")
            outline = self.segmenter.segment(extracted.source_frames)
            ir = ProgressiveReviewIR(
                document_id=extracted.document_id,
                title=extracted.title,
                document_type=extracted.document_type,
                source_frames=extracted.source_frames,
                outline=outline,
                claims=[],
                evidence_cards=[],
                pipeline_version=PIPELINE_VERSION,
                is_partial=True,
            )
            self._write_ir(job_id, ir)

            self._set_stage(state, "planning")
            plan = provider.plan_review(extracted, outline)
            state.block_statuses = self._block_statuses(plan.block_ids, outline)
            state.progress.total_blocks = len(state.block_statuses)
            ir.generation_plan = plan
            ir.layout_spec = provider.build_layout_spec(extracted, outline, plan)
            ir.visual_blocks = self._supported_visual_blocks(provider.generate_visual_blocks(extracted, outline))
            ir.block_statuses = state.block_statuses
            self._write_ir(job_id, ir)
            self._write_state(state)

            self._run_block(state, ir, "overview", "generating_overview")
            overview = provider.generate_overview(extracted, outline)
            ir.outline = [overview]
            self._complete_block(state, "overview")
            ir.block_statuses = state.block_statuses
            self._write_ir(job_id, ir)

            self._set_stage(state, "generating_blocks")
            section_claims: dict[str, list] = {}
            for section in outline:
                self._run_block(state, ir, f"section:{section.section_id}", "generating_blocks")
                provider.generate_section_brief(section, extracted)
                self._complete_block(state, f"section:{section.section_id}")
                ir.block_statuses = state.block_statuses
                self._write_ir(job_id, ir)

                self._run_block(state, ir, f"claims:{section.section_id}", "generating_blocks")
                claims = self._supported_claims(provider.generate_claims(section, extracted, len(ir.claims) + 1))
                ir.claims.extend(claims)
                section.key_claim_ids = [claim.claim_id for claim in claims]
                section_claims[section.section_id] = claims
                state.claim_count = len(ir.claims)
                self._complete_block(state, f"claims:{section.section_id}")
                ir.block_statuses = state.block_statuses
                self._write_ir(job_id, ir)

                self._run_block(state, ir, f"evidence:{section.section_id}", "generating_blocks")
                cards = self._supported_evidence(provider.generate_evidence_cards(claims, extracted, len(ir.evidence_cards) + 1))
                ir.evidence_cards.extend(cards)
                state.evidence_count = len(ir.evidence_cards)
                self._complete_block(state, f"evidence:{section.section_id}")
                ir.block_statuses = state.block_statuses
                self._write_ir(job_id, ir)

            self._run_block(state, ir, "validation", "validating")
            validation = self.validator.validate(ir)
            ir.validation = provider.validate_support(validation)
            ir.is_partial = False
            self._complete_block(state, "validation")
            self._set_stage(state, "complete", status="complete")
            state.is_partial = False
            state.valid = ir.validation.valid if ir.validation else None
            state.warnings = ir.validation.warnings if ir.validation else []
            ir.block_statuses = state.block_statuses
            self._write_ir(job_id, ir)
            self._write_state(state)
            return ir
        except Exception as exc:
            state.stage = "failed"
            state.status = "failed"
            state.error = str(exc)
            state.is_partial = True
            state.updated_at = now_iso()
            if state.current_block_id:
                self._mark_block(state, state.current_block_id, "failed", str(exc))
            if ir:
                ir.is_partial = True
                ir.block_statuses = state.block_statuses
                self._write_ir(job_id, ir)
            self._write_state(state)
            raise

    def _read_or_create_state(self, job_id: str, provider_name: str | None) -> WorkflowState:
        try:
            return WorkflowState.model_validate(self.store.read_workflow(job_id))
        except FileNotFoundError:
            return self.initialize_queued_job(job_id, provider_name or "mock")

    def _set_stage(self, state: WorkflowState, stage: str, status: str = "processing") -> None:
        state.stage = stage
        state.status = status
        state.updated_at = now_iso()
        self._write_state(state)

    def _run_block(self, state: WorkflowState, ir: ProgressiveReviewIR, block_id: str, stage: str) -> None:
        self._set_stage(state, stage)
        state.current_block_id = block_id
        self._mark_block(state, block_id, "running")
        ir.block_statuses = state.block_statuses
        self._write_ir(state.job_id, ir)
        self._write_state(state)

    def _complete_block(self, state: WorkflowState, block_id: str) -> None:
        self._mark_block(state, block_id, "complete")
        state.current_block_id = None
        state.progress.completed_blocks = len([block for block in state.block_statuses if block.status == "complete"])
        state.updated_at = now_iso()
        self._write_state(state)

    def _mark_block(self, state: WorkflowState, block_id: str, status: str, error: str | None = None) -> None:
        for block in state.block_statuses:
            if block.block_id == block_id:
                block.status = status
                block.error = error
                block.updated_at = now_iso()
                return

    def _block_statuses(self, block_ids: list[str], outline: list[ReviewSection]) -> list[ReviewBlockStatus]:
        section_by_id = {section.section_id: section for section in outline}
        statuses: list[ReviewBlockStatus] = []
        for block_id in block_ids:
            block_type, _, section_id = block_id.partition(":")
            section = section_by_id.get(section_id)
            title = {
                "overview": "Document overview",
                "section": f"Section brief: {section.title if section else section_id}",
                "claims": f"Claims: {section.title if section else section_id}",
                "evidence": f"Evidence: {section.title if section else section_id}",
                "validation": "Validation",
            }.get(block_type, block_id)
            statuses.append(
                ReviewBlockStatus(
                    block_id=block_id,
                    type=block_type,
                    title=title,
                    source_frame_ids=section.source_frame_ids if section else [],
                )
            )
        return statuses

    def _supported_claims(self, claims: list) -> list:
        return [claim for claim in claims if claim.source_refs]

    def _supported_evidence(self, cards: list) -> list:
        return [card for card in cards if card.source_refs]

    def _supported_visual_blocks(self, blocks: list) -> list:
        return [block for block in blocks if block.type == "agent_slot" or block.source_refs]

    def _write_ir(self, job_id: str, ir: ProgressiveReviewIR) -> None:
        self.store.write_json(job_id, "ir.json", ir.model_dump(mode="json"))

    def _write_state(self, state: WorkflowState) -> None:
        state.updated_at = now_iso()
        data = state.model_dump(mode="json")
        self.store.write_workflow(state.job_id, data)
        summary = {key: value for key, value in data.items() if key != "block_statuses"}
        self.store.write_status(state.job_id, summary)
