from app.models.review_ir import ProgressiveReviewIR, ReviewSection, ValidationResult


class IRValidator:
    def validate(self, ir: ProgressiveReviewIR) -> ValidationResult:
        warnings: list[str] = []
        frame_by_id = {frame.source_frame_id: frame for frame in ir.source_frames}
        unit_by_id = {
            unit.unit_id: unit
            for frame in ir.source_frames
            for unit in frame.units
        }

        for claim in ir.claims:
            if not claim.source_refs:
                warnings.append(f"{claim.claim_id} has no source refs")
            for ref in claim.source_refs:
                frame = frame_by_id.get(ref.source_frame_id)
                if not frame:
                    warnings.append(f"{claim.claim_id} references missing frame {ref.source_frame_id}")
                    continue
                if ref.source_unit_id and ref.source_unit_id not in unit_by_id:
                    warnings.append(f"{claim.claim_id} references missing unit {ref.source_unit_id}")
                if ref.quote and ref.quote not in " ".join(frame.text.split()):
                    if ref.quote not in frame.text:
                        warnings.append(f"{claim.claim_id} quote not found on {ref.source_frame_id}")

        for evidence in ir.evidence_cards:
            if not evidence.source_refs:
                warnings.append(f"{evidence.evidence_id} has no source refs")
            if evidence.claim_id not in {claim.claim_id for claim in ir.claims}:
                warnings.append(f"{evidence.evidence_id} references missing claim {evidence.claim_id}")

        for block in ir.visual_blocks:
            if block.type != "agent_slot" and not block.source_refs:
                warnings.append(f"{block.block_id} has no source refs")
            for ref in block.source_refs:
                frame = frame_by_id.get(ref.source_frame_id)
                if not frame:
                    warnings.append(f"{block.block_id} references missing frame {ref.source_frame_id}")
                    continue
                if ref.source_unit_id and ref.source_unit_id not in unit_by_id:
                    warnings.append(f"{block.block_id} references missing unit {ref.source_unit_id}")

        for section in self._flatten_sections(ir.outline):
            if section.section_id != "overview" and not section.source_frame_ids:
                warnings.append(f"{section.section_id} references no source pages")
            for frame_id in section.source_frame_ids:
                if frame_id not in frame_by_id:
                    warnings.append(f"{section.section_id} references missing frame {frame_id}")

        return ValidationResult(valid=not warnings, warnings=warnings)

    def _flatten_sections(self, sections: list[ReviewSection]) -> list[ReviewSection]:
        flattened: list[ReviewSection] = []
        for section in sections:
            flattened.append(section)
            flattened.extend(self._flatten_sections(section.children))
        return flattened
