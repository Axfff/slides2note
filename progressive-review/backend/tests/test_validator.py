from app.models.review_ir import Claim, ProgressiveReviewIR, ReviewSection, SourceRef
from app.models.source import SourceFrame, SourceUnit
from app.services.validator import IRValidator


def test_validator_accepts_claim_with_existing_frame_unit_and_quote():
    frame = SourceFrame(
        source_frame_id="page_1",
        index=1,
        image_path="pages/page_001.png",
        text="Class P contains languages decidable in polynomial time.",
        units=[
            SourceUnit(
                unit_id="page_1_text_1",
                text="Class P contains languages decidable in polynomial time.",
                bbox=(10, 20, 30, 40),
            )
        ],
    )
    ir = ProgressiveReviewIR(
        document_id="job_1",
        title="Test",
        document_type="pdf",
        source_frames=[frame],
        outline=[
            ReviewSection(
                section_id="section_1",
                title="Class P",
                level=1,
                summary="Summary",
                source_frame_ids=["page_1"],
            )
        ],
        claims=[
            Claim(
                claim_id="claim_1",
                text="Class P is about polynomial-time decidability.",
                source_refs=[
                    SourceRef(
                        source_frame_id="page_1",
                        source_unit_id="page_1_text_1",
                        page_index=1,
                        quote="Class P contains languages decidable in polynomial time.",
                    )
                ],
            )
        ],
        evidence_cards=[],
        pipeline_version="test",
    )

    result = IRValidator().validate(ir)

    assert result.valid
    assert result.warnings == []


def test_validator_warns_for_missing_source_ref():
    ir = ProgressiveReviewIR(
        document_id="job_1",
        title="Test",
        document_type="pdf",
        source_frames=[],
        outline=[],
        claims=[Claim(claim_id="claim_1", text="Unsupported claim", source_refs=[])],
        evidence_cards=[],
        pipeline_version="test",
    )

    result = IRValidator().validate(ir)

    assert not result.valid
    assert "claim_1 has no source refs" in result.warnings

