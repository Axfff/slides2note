from pathlib import Path
from uuid import uuid4

import fitz

from app.models.source import ExtractedDocument, SourceFrame, SourceUnit


def _first_non_empty_line(text: str, fallback: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:140]
    return fallback


class PDFExtractor:
    def extract(self, pdf_path: Path, pages_dir: Path, document_id: str | None = None) -> ExtractedDocument:
        pages_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(pdf_path)
        frames: list[SourceFrame] = []
        title = pdf_path.stem
        document_id = document_id or uuid4().hex

        for page_number, page in enumerate(doc, start=1):
            frame_id = f"page_{page_number}"
            image_name = f"page_{page_number:03d}.png"
            image_path = pages_dir / image_name
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pix.save(image_path)

            text = page.get_text("text").strip()
            if page_number == 1:
                title = _first_non_empty_line(text, title)

            units: list[SourceUnit] = []
            for block_index, block in enumerate(page.get_text("blocks"), start=1):
                if len(block) < 5:
                    continue
                x0, y0, x1, y1, block_text = block[:5]
                block_text = str(block_text).strip()
                if not block_text:
                    continue
                units.append(
                    SourceUnit(
                        unit_id=f"{frame_id}_text_{block_index}",
                        type="text_block",
                        text=block_text,
                        bbox=(float(x0), float(y0), float(x1), float(y1)),
                    )
                )

            rect = page.rect
            frames.append(
                SourceFrame(
                    source_frame_id=frame_id,
                    index=page_number,
                    image_path=f"pages/{image_name}",
                    width=float(rect.width),
                    height=float(rect.height),
                    text=text,
                    units=units,
                )
            )

        doc.close()
        return ExtractedDocument(
            document_id=document_id,
            title=title,
            document_type="pdf",
            source_frames=frames,
        )

