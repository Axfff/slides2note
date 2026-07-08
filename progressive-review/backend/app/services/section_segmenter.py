import re

from app.models.review_ir import ReviewSection
from app.models.source import SourceFrame


HEADING_PATTERNS = [
    re.compile(r"^\s*part\s+\w+", re.IGNORECASE),
    re.compile(r"^\s*textbook\s+(def|thm|theorem)", re.IGNORECASE),
    re.compile(r"^\s*example\b", re.IGNORECASE),
    re.compile(r"^\s*deeper\b", re.IGNORECASE),
    re.compile(r"^\s*broader\b", re.IGNORECASE),
    re.compile(r"^\s*summary\b", re.IGNORECASE),
    re.compile(r"^\s*\d+(\.\d+)*\s+.+"),
]


def _is_heading(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned or len(cleaned) > 120:
        return False
    if any(pattern.match(cleaned) for pattern in HEADING_PATTERNS):
        return True
    words = cleaned.split()
    return 2 <= len(words) <= 10 and cleaned.upper() == cleaned and any(ch.isalpha() for ch in cleaned)


def _summary_from_text(text: str, limit: int = 320) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "No selectable text was extracted for this section."
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


class SectionSegmenter:
    def segment(self, frames: list[SourceFrame]) -> list[ReviewSection]:
        sections: list[ReviewSection] = []

        for frame in frames:
            lines = [line.strip() for line in frame.text.splitlines() if line.strip()]
            heading = next((line for line in lines if _is_heading(line)), None)
            if not heading:
                heading = f"Page {frame.index}"

            sections.append(
                ReviewSection(
                    section_id=f"section_{len(sections) + 1}",
                    title=heading[:120],
                    level=1,
                    summary=_summary_from_text(frame.text),
                    source_frame_ids=[frame.source_frame_id],
                    full_notes=frame.text[:2000] if frame.text else None,
                )
            )

        if not sections:
            return [
                ReviewSection(
                    section_id="section_1",
                    title="Empty document",
                    level=1,
                    summary="No pages were extracted.",
                    source_frame_ids=[],
                )
            ]

        return sections

