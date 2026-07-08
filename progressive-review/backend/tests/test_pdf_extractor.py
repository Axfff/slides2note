from pathlib import Path

import fitz

from app.services.pdf_extractor import PDFExtractor


def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Week 8: Time Complexity & Class P")
    page.insert_text((72, 104), "Textbook Def. 7.12 - P is the class of polynomial-time decidable languages.")
    doc.save(path)
    doc.close()


def test_pdf_extractor_renders_pages_and_extracts_text(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pages_dir = tmp_path / "pages"
    _make_pdf(pdf_path)

    extracted = PDFExtractor().extract(pdf_path, pages_dir, document_id="job_1")

    assert extracted.document_id == "job_1"
    assert extracted.title == "Week 8: Time Complexity & Class P"
    assert len(extracted.source_frames) == 1
    assert "Textbook Def." in extracted.source_frames[0].text
    assert extracted.source_frames[0].units
    assert (pages_dir / "page_001.png").exists()

