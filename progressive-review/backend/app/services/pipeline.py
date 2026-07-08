from pathlib import Path
from datetime import datetime, timezone

from app.models.review_ir import ProgressiveReviewIR
from app.services.pdf_extractor import PDFExtractor
from app.services.review_generator import ReviewGenerator
from app.services.section_segmenter import SectionSegmenter
from app.services.validator import IRValidator
from app.storage.file_store import FileStore


class ReviewPipeline:
    def __init__(self, store: FileStore | None = None):
        self.store = store or FileStore()
        self.extractor = PDFExtractor()
        self.segmenter = SectionSegmenter()
        self.generator = ReviewGenerator()
        self.validator = IRValidator()

    def run(self, job_id: str, pdf_path: Path) -> ProgressiveReviewIR:
        started_at = datetime.now(timezone.utc).isoformat()
        self.store.write_status(job_id, {"job_id": job_id, "status": "processing", "created_at": started_at, "updated_at": started_at})
        extracted = self.extractor.extract(pdf_path, self.store.pages_dir(job_id), document_id=job_id)
        self.store.write_json(job_id, "source_frames.json", extracted.model_dump(mode="json"))

        outline = self.segmenter.segment(extracted.source_frames)
        ir = self.generator.generate(extracted, outline)
        ir.validation = self.validator.validate(ir)
        self.store.write_json(job_id, "ir.json", ir.model_dump(mode="json"))
        self.store.write_status(
            job_id,
            {
                "job_id": job_id,
                "status": "complete",
                "title": ir.title,
                "page_count": len(ir.source_frames),
                "claim_count": len(ir.claims),
                "evidence_count": len(ir.evidence_cards),
                "created_at": started_at,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "valid": ir.validation.valid if ir.validation else False,
                "warnings": ir.validation.warnings if ir.validation else [],
            },
        )
        return ir
