from app.models.source import ExtractedDocument, SourceFrame, SourceUnit
from app.services.review_generator import ReviewGenerator
from app.services.section_segmenter import SectionSegmenter
from app.services.validator import IRValidator


def test_generated_claims_and_evidence_have_source_refs():
    extracted = ExtractedDocument(
        document_id="job_1",
        title="Week 8",
        source_frames=[
            SourceFrame(
                source_frame_id="page_1",
                index=1,
                image_path="pages/page_001.png",
                text="Textbook Def. 7.12 - P is the class of languages decidable in polynomial time.",
                units=[
                    SourceUnit(
                        unit_id="page_1_text_1",
                        text="Textbook Def. 7.12 - P is the class of languages decidable in polynomial time.",
                        bbox=(1, 2, 3, 4),
                    )
                ],
            )
        ],
    )

    outline = SectionSegmenter().segment(extracted.source_frames)
    ir = ReviewGenerator().generate(extracted, outline)
    ir.validation = IRValidator().validate(ir)

    assert ir.claims
    assert all(claim.source_refs for claim in ir.claims)
    assert ir.evidence_cards
    assert all(card.source_refs for card in ir.evidence_cards)
    assert ir.validation.valid

