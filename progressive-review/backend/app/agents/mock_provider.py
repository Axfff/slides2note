import re

from app.agents.base import AgentProvider
from app.models.review_ir import (
    AgentLayoutSlot,
    AgentLayoutSpec,
    Claim,
    EvidenceCard,
    ReviewGenerationPlan,
    ReviewSection,
    SourceRef,
    ValidationResult,
    VisualInteractiveBlock,
)
from app.models.source import ExtractedDocument, SourceFrame, SourceUnit


CLAIM_PATTERNS = [
    re.compile(r"\b(def\.?|definition|thm\.?|theorem|lemma|claim|example)\b", re.IGNORECASE),
    re.compile(r"\b(is|are|means|implies|decidable|recognizable|polynomial|complexity)\b", re.IGNORECASE),
]


def clean(text: str) -> str:
    return " ".join(text.split())


def source_ref(frame: SourceFrame, unit: SourceUnit | None = None) -> SourceRef:
    quote = clean(unit.text if unit else frame.text)
    return SourceRef(
        source_frame_id=frame.source_frame_id,
        source_unit_id=unit.unit_id if unit else None,
        page_index=frame.index,
        bbox=unit.bbox if unit else None,
        quote=quote[:280] if quote else None,
    )


def frame_text(extracted: ExtractedDocument, frame_ids: list[str]) -> str:
    frames = {frame.source_frame_id: frame for frame in extracted.source_frames}
    return "\n".join(frames[frame_id].text for frame_id in frame_ids if frame_id in frames)


class MockAgentProvider(AgentProvider):
    name = "mock"

    def plan_review(self, extracted: ExtractedDocument, outline: list[ReviewSection]) -> ReviewGenerationPlan:
        block_ids = ["overview"]
        for section in outline:
            block_ids.extend([f"section:{section.section_id}", f"claims:{section.section_id}", f"evidence:{section.section_id}"])
        block_ids.append("validation")
        return ReviewGenerationPlan(
            provider=self.name,
            block_ids=block_ids,
            layout_strategy="source_linked_cheatsheet",
            quality_targets=[
                "Start with a tutorial-style hero and exam map.",
                "Prefer concept cards, callouts, tables, and question banks over flat prose.",
                "Every authored visual or interactive block must keep source references.",
            ],
            allowed_visual_block_types=[
                "hero",
                "visual_summary",
                "concept_grid",
                "callout",
                "comparison_table",
                "question_bank",
                "interactive_checklist",
                "source_timeline",
                "agent_slot",
            ],
        )

    def generate_overview(self, extracted: ExtractedDocument, outline: list[ReviewSection]) -> ReviewSection:
        page_count = len(extracted.source_frames)
        first_text = clean(extracted.source_frames[0].text) if extracted.source_frames else ""
        summary = f"{extracted.title} spans {page_count} page{'s' if page_count != 1 else ''}. {first_text[:420]}"
        return ReviewSection(
            section_id="overview",
            title="Document Overview",
            level=0,
            summary=summary.strip(),
            source_frame_ids=[frame.source_frame_id for frame in extracted.source_frames[: min(3, page_count)]],
            children=outline,
        )

    def generate_section_brief(self, section: ReviewSection, extracted: ExtractedDocument) -> ReviewSection:
        text = clean(frame_text(extracted, section.source_frame_ids))
        section.summary = text[:360] + ("..." if len(text) > 360 else "") if text else section.summary
        section.full_notes = text[:2400] if text else section.full_notes
        return section

    def generate_claims(self, section: ReviewSection, extracted: ExtractedDocument, start_index: int) -> list[Claim]:
        frames = {frame.source_frame_id: frame for frame in extracted.source_frames}
        claims: list[Claim] = []
        for frame_id in section.source_frame_ids:
            frame = frames.get(frame_id)
            if not frame:
                continue
            units = [unit for unit in frame.units if any(pattern.search(unit.text) for pattern in CLAIM_PATTERNS)] or frame.units[:2]
            for unit in units[:4]:
                claim_id = f"claim_{start_index + len(claims)}"
                unit_text = clean(unit.text)
                sentence = re.split(r"(?<=[.!?])\s+", unit_text)[0]
                ref = source_ref(frame, unit)
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        text=sentence[:240] + ("..." if len(sentence) > 240 else ""),
                        explanation=f"Derived from extracted source text: {unit_text[:220]}",
                        source_refs=[ref],
                        confidence=0.72,
                        tags=self._tags(unit_text),
                        progressive_level="standard",
                    )
                )
        section.key_claim_ids = [claim.claim_id for claim in claims]
        return claims

    def generate_evidence_cards(self, claims: list[Claim], extracted: ExtractedDocument, start_index: int) -> list[EvidenceCard]:
        cards: list[EvidenceCard] = []
        for claim in claims:
            if not claim.source_refs:
                continue
            ref = claim.source_refs[0]
            cards.append(
                EvidenceCard(
                    evidence_id=f"evidence_{start_index + len(cards)}",
                    claim_id=claim.claim_id,
                    title=f"Evidence from page {ref.page_index or ref.source_frame_id}",
                    evidence_text=ref.quote or claim.text,
                    why_it_matters="This excerpt anchors the generated claim to the original source.",
                    caveat="Generated by the mock agent; inspect the source page for full context.",
                    source_refs=[ref],
                )
            )
        return cards

    def validate_support(self, validation: ValidationResult) -> ValidationResult:
        return validation

    def build_layout_spec(
        self,
        extracted: ExtractedDocument,
        outline: list[ReviewSection],
        plan: ReviewGenerationPlan,
    ) -> AgentLayoutSpec:
        primary_frames = [frame.source_frame_id for frame in extracted.source_frames[: min(3, len(extracted.source_frames))]]
        return AgentLayoutSpec(
            mode="agent_composed",
            density="comfortable",
            style_preset="cheatsheet",
            reading_width_px=1180,
            review_column_min_px=460,
            source_column_min_px=380,
            slots=[
                AgentLayoutSlot(
                    slot_id="cheatsheet_hero_slot",
                    title="Cheatsheet Hero",
                    placement="hero",
                    allowed_block_types=["hero", "visual_summary"],
                    source_frame_ids=primary_frames,
                    description="Reserved for a polished source-linked title, lead, and metadata strip.",
                ),
                AgentLayoutSlot(
                    slot_id="overview_visual_slot",
                    title="Overview Visual",
                    placement="after_overview",
                    allowed_block_types=["concept_grid", "visual_summary", "callout", "comparison_table"],
                    source_frame_ids=primary_frames,
                    description="Reserved for tutorial cards and source-linked cheat-sheet summaries.",
                ),
                AgentLayoutSlot(
                    slot_id="interactive_review_slot",
                    title="Interactive Review",
                    placement="before_sections",
                    allowed_block_types=["interactive_checklist", "source_timeline", "question_bank"],
                    source_frame_ids=primary_frames,
                    description="Reserved for interactive checkpoints generated from source-backed blocks.",
                ),
                AgentLayoutSlot(
                    slot_id="agent_custom_slot",
                    title="Agent Custom Section",
                    placement="after_sections",
                    allowed_block_types=["agent_slot", "visual_summary", "interactive_checklist", "source_timeline"],
                    source_frame_ids=primary_frames,
                    description="Reserved for a future provider-selected module.",
                ),
            ],
            quality_targets=[
                "A compact tutorial should be readable without opening the source pane.",
                "Generated blocks should be visually varied but still cite source pages.",
                "Use tables/callouts/questions when the source is educational or exam-oriented.",
            ],
            notes="Renderer accepts structured block payloads only; raw HTML is intentionally not part of the contract.",
        )

    def generate_visual_blocks(
        self,
        extracted: ExtractedDocument,
        outline: list[ReviewSection],
    ) -> list[VisualInteractiveBlock]:
        if not extracted.source_frames:
            return []
        first_frame = extracted.source_frames[0]
        first_ref = source_ref(first_frame, first_frame.units[0] if first_frame.units else None)
        page_refs = [SourceRef(source_frame_id=frame.source_frame_id, page_index=frame.index) for frame in extracted.source_frames]
        section_titles = [section.title for section in outline[:6]]
        title_tokens = [token for token in re.split(r"[:&|·-]", extracted.title) if token.strip()]
        focus = clean(title_tokens[-1] if title_tokens else extracted.title)
        concept_items = self._concept_items(extracted, outline)
        table_rows = self._comparison_rows(extracted)
        questions = self._question_bank(extracted)
        return [
            VisualInteractiveBlock(
                block_id="cheatsheet_hero",
                type="hero",
                title=extracted.title,
                placement="hero",
                source_refs=[first_ref],
                payload={
                    "kicker": "Source-linked cheatsheet",
                    "lead": (
                        f"This review reorganizes {extracted.title} into a compact tutorial workspace. "
                        "Skim the map first, then open claims, evidence, and source pages when verification matters."
                    ),
                    "pills": [
                        f"{len(extracted.source_frames)} source pages",
                        f"{sum(len(frame.units) for frame in extracted.source_frames)} extracted units",
                        "Source links preserved",
                    ],
                    "code_lines": [
                        f"read_fast('{focus[:42]}')",
                        "expand_when_needed(section)",
                        "verify_every_claim(source_ref)",
                    ],
                },
            ),
            VisualInteractiveBlock(
                block_id="visual_summary",
                type="visual_summary",
                title="Document Snapshot",
                placement="after_overview",
                source_refs=[first_ref],
                payload={
                    "stats": [
                        {"label": "Pages", "value": len(extracted.source_frames)},
                        {"label": "Sections", "value": len(outline)},
                        {"label": "Source units", "value": sum(len(frame.units) for frame in extracted.source_frames)},
                    ],
                    "items": section_titles,
                },
            ),
            VisualInteractiveBlock(
                block_id="exam_map",
                type="concept_grid",
                title="Exam Map",
                placement="after_overview",
                source_refs=[first_ref],
                payload={"items": concept_items},
            ),
            VisualInteractiveBlock(
                block_id="source_backed_callout",
                type="callout",
                title="How to Use This Review",
                placement="after_overview",
                source_refs=[first_ref],
                payload={
                    "tone": "key",
                    "body": "Treat generated prose as a guided index into the document. Open source links for every claim that matters.",
                },
            ),
            VisualInteractiveBlock(
                block_id="source_comparison_table",
                type="comparison_table",
                title="Source Pattern Table",
                placement="after_overview",
                source_refs=page_refs[: min(5, len(page_refs))],
                payload={
                    "columns": ["Page", "Signal", "Why it matters"],
                    "rows": table_rows,
                },
            ),
            VisualInteractiveBlock(
                block_id="source_timeline",
                type="source_timeline",
                title="Source Flow",
                placement="before_sections",
                source_refs=page_refs[:8],
                payload={
                    "events": [
                        {
                            "label": f"Page {frame.index}",
                            "summary": clean(frame.text)[:120],
                            "source_ref": {"source_frame_id": frame.source_frame_id, "page_index": frame.index},
                        }
                        for frame in extracted.source_frames[:8]
                    ]
                },
            ),
            VisualInteractiveBlock(
                block_id="question_bank",
                type="question_bank",
                title="Source Questions",
                placement="before_sections",
                source_refs=[first_ref],
                payload={"questions": questions},
            ),
            VisualInteractiveBlock(
                block_id="review_checkpoints",
                type="interactive_checklist",
                title="Review Checkpoints",
                placement="before_sections",
                source_refs=[first_ref],
                payload={
                    "items": [
                        {"id": "map", "label": "Skim the structure map", "source_ref": first_ref.model_dump(mode="json")},
                        {"id": "claims", "label": "Open key claims", "source_ref": first_ref.model_dump(mode="json")},
                        {"id": "evidence", "label": "Verify evidence against the source page", "source_ref": first_ref.model_dump(mode="json")},
                    ]
                },
            ),
            VisualInteractiveBlock(
                block_id="agent_reserved_layout",
                type="agent_slot",
                title="Agent-Composed Module",
                placement="after_sections",
                source_refs=[first_ref],
                payload={
                    "slot_id": "agent_custom_slot",
                    "accepted": ["visual_summary", "interactive_checklist", "source_timeline"],
                },
            ),
        ]

    def _concept_items(self, extracted: ExtractedDocument, outline: list[ReviewSection]) -> list[dict]:
        fallback_titles = [section.title for section in outline[:4]] or [extracted.title]
        tags = ["Concept", "Tool", "Proof", "Practice"]
        items = []
        for index, title in enumerate(fallback_titles[:4]):
            items.append(
                {
                    "tag": tags[index % len(tags)],
                    "title": title[:80],
                    "body": "Open the linked source page and compare the generated claim with the original wording.",
                }
            )
        return items

    def _comparison_rows(self, extracted: ExtractedDocument) -> list[list[str]]:
        rows = []
        for frame in extracted.source_frames[:5]:
            signal = clean(frame.units[0].text if frame.units else frame.text)[:90]
            rows.append([f"Page {frame.index}", signal, "Candidate anchor for a sourced review block."])
        return rows

    def _question_bank(self, extracted: ExtractedDocument) -> list[dict]:
        candidates = []
        for frame in extracted.source_frames:
            for unit in frame.units:
                text = clean(unit.text)
                if "?" in text or re.search(r"\b(DEEPER|BROADER|Task|Example)\b", text, re.IGNORECASE):
                    candidates.append(
                        {
                            "label": f"Page {frame.index}",
                            "question": text[:180],
                            "answer": "Use the surrounding source text as the verification context before relying on the generated answer.",
                            "source_ref": source_ref(frame, unit).model_dump(mode="json"),
                        }
                    )
                if len(candidates) >= 6:
                    return candidates
        return [
            {
                "label": "Review prompt",
                "question": f"What are the main ideas in {extracted.title}?",
                "answer": "Start with the overview, then verify each claim against its source page.",
                "source_ref": source_ref(extracted.source_frames[0], extracted.source_frames[0].units[0] if extracted.source_frames[0].units else None).model_dump(mode="json"),
            }
        ]

    def _tags(self, text: str) -> list[str]:
        lowered = text.lower()
        tags = []
        for key in ["definition", "def", "theorem", "thm", "example", "complexity", "polynomial"]:
            if key in lowered:
                tags.append("definition" if key == "def" else "theorem" if key == "thm" else key)
        return sorted(set(tags)) or ["source-linked"]
