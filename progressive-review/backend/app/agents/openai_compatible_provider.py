import json
import re
from abc import abstractmethod
from typing import Any

from app.agents.mock_provider import MockAgentProvider, clean, source_ref
from app.agents.prompts import SOURCE_LINKED_REVIEW_SYSTEM_PROMPT
from app.models.review_ir import Claim, EvidenceCard, ReviewSection, VisualInteractiveBlock
from app.models.source import ExtractedDocument, SourceFrame, SourceUnit


class OpenAICompatibleAgentProvider(MockAgentProvider):
    """Shared source-disciplined agent logic for OpenAI-compatible chat APIs."""

    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _client(self):
        raise NotImplementedError

    def _llm_enabled(self) -> bool:
        api_key = getattr(self, "api_key", "")
        return bool(api_key and api_key != "test-key")

    def _json_chat(self, task: str, payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
        if not self._llm_enabled():
            return fallback
        try:
            client = self._client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SOURCE_LINKED_REVIEW_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task": task,
                                "requirements": [
                                    "Return strict JSON only.",
                                    "Do not return HTML.",
                                    "Prefer concise tutorial-style prose.",
                                    "Only use facts present in the provided source snippets.",
                                ],
                                "input": payload,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                stream=False,
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else fallback
        except Exception:
            return fallback

    def generate_overview(self, extracted: ExtractedDocument, outline: list[ReviewSection]) -> ReviewSection:
        overview = super().generate_overview(extracted, outline)
        source_text = self._document_context(extracted, max_chars=5000)
        parsed = self._json_chat(
            "Write a high-quality document overview for a progressive source-linked review.",
            {
                "document_title": extracted.title,
                "page_count": len(extracted.source_frames),
                "outline_titles": [section.title for section in outline[:12]],
                "source_text": source_text,
                "schema": {"summary": "string"},
            },
            {},
        )
        summary = str(parsed.get("summary", "")).strip()
        if summary:
            overview.summary = summary
        return overview

    def generate_section_brief(self, section: ReviewSection, extracted: ExtractedDocument) -> ReviewSection:
        fallback = super().generate_section_brief(section, extracted)
        parsed = self._json_chat(
            "Summarize one source section as tutorial notes.",
            {
                "section_title": section.title,
                "source_pages": section.source_frame_ids,
                "source_text": self._section_context(section, extracted, max_chars=6500),
                "schema": {
                    "summary": "2-4 sentence source-grounded section summary",
                    "full_notes": "optional concise study notes",
                },
            },
            {},
        )
        summary = str(parsed.get("summary", "")).strip()
        full_notes = str(parsed.get("full_notes", "")).strip()
        if summary:
            fallback.summary = summary
        if full_notes:
            fallback.full_notes = full_notes
        return fallback

    def generate_claims(self, section: ReviewSection, extracted: ExtractedDocument, start_index: int) -> list[Claim]:
        candidates = self._claim_candidates(section, extracted)
        if not candidates:
            return super().generate_claims(section, extracted, start_index)

        parsed = self._json_chat(
            "Extract high-value, source-grounded claims from source snippets.",
            {
                "section_title": section.title,
                "candidates": candidates,
                "schema": {
                    "claims": [
                        {
                            "unit_id": "must match one candidate unit_id",
                            "text": "claim text",
                            "explanation": "why this claim matters",
                            "tags": ["short tags"],
                        }
                    ]
                },
            },
            {},
        )
        by_unit = self._unit_lookup(extracted)
        claims: list[Claim] = []
        for item in parsed.get("claims", []):
            if not isinstance(item, dict):
                continue
            unit_id = str(item.get("unit_id", "")).strip()
            frame_unit = by_unit.get(unit_id)
            text = clean(str(item.get("text", "")))
            if not frame_unit or not text:
                continue
            frame, unit = frame_unit
            tags = item.get("tags", [])
            claims.append(
                Claim(
                    claim_id=f"claim_{start_index + len(claims)}",
                    text=text[:280],
                    explanation=clean(str(item.get("explanation", "")))[:420] or None,
                    source_refs=[source_ref(frame, unit)],
                    confidence=0.78,
                    tags=[clean(str(tag))[:32] for tag in tags if clean(str(tag))][:5] or ["ai-source-linked"],
                    progressive_level="standard",
                )
            )
            if len(claims) >= 6:
                break

        if claims:
            section.key_claim_ids = [claim.claim_id for claim in claims]
            return claims
        return super().generate_claims(section, extracted, start_index)

    def generate_evidence_cards(self, claims: list[Claim], extracted: ExtractedDocument, start_index: int) -> list[EvidenceCard]:
        fallback_cards = super().generate_evidence_cards(claims, extracted, start_index)
        parsed = self._json_chat(
            "Write concise evidence card copy for already source-linked claims.",
            {
                "claims": [
                    {
                        "claim_id": claim.claim_id,
                        "claim": claim.text,
                        "quote": claim.source_refs[0].quote if claim.source_refs else "",
                        "page": claim.source_refs[0].page_index if claim.source_refs else None,
                    }
                    for claim in claims
                    if claim.source_refs
                ],
                "schema": {
                    "cards": [
                        {
                            "claim_id": "existing claim_id",
                            "title": "short title",
                            "evidence_text": "quote/paraphrase from provided quote",
                            "why_it_matters": "short explanation",
                            "caveat": "optional caveat",
                        }
                    ]
                },
            },
            {},
        )
        by_claim = {claim.claim_id: claim for claim in claims if claim.source_refs}
        cards: list[EvidenceCard] = []
        for item in parsed.get("cards", []):
            if not isinstance(item, dict):
                continue
            claim = by_claim.get(str(item.get("claim_id", "")))
            if not claim:
                continue
            cards.append(
                EvidenceCard(
                    evidence_id=f"evidence_{start_index + len(cards)}",
                    claim_id=claim.claim_id,
                    title=clean(str(item.get("title", "")))[:120] or f"Evidence for {claim.claim_id}",
                    evidence_text=clean(str(item.get("evidence_text", "")))[:700] or (claim.source_refs[0].quote or claim.text),
                    why_it_matters=clean(str(item.get("why_it_matters", "")))[:500]
                    or "This source excerpt supports the generated claim.",
                    caveat=clean(str(item.get("caveat", "")))[:300] or None,
                    source_refs=[claim.source_refs[0]],
                )
            )
        return cards or fallback_cards

    def generate_visual_blocks(
        self,
        extracted: ExtractedDocument,
        outline: list[ReviewSection],
    ) -> list[VisualInteractiveBlock]:
        blocks = super().generate_visual_blocks(extracted, outline)
        parsed = self._json_chat(
            "Improve structured cheatsheet layout payloads for a polished educational review.",
            {
                "document_title": extracted.title,
                "outline_titles": [section.title for section in outline[:10]],
                "source_text": self._document_context(extracted, max_chars=5000),
                "schema": {
                    "hero": {"lead": "string", "pills": ["string"], "code_lines": ["string"]},
                    "concept_grid": {
                        "items": [{"tag": "Concept|Tool|Proof|Practice", "title": "string", "body": "string"}]
                    },
                    "callout": {"body": "string", "tone": "key|warn|exam|default"},
                    "question_bank": {
                        "questions": [{"label": "string", "question": "string", "answer": "string"}]
                    },
                },
            },
            {},
        )
        self._merge_visual_payload(blocks, "cheatsheet_hero", parsed.get("hero"))
        self._merge_visual_payload(blocks, "exam_map", parsed.get("concept_grid"))
        self._merge_visual_payload(blocks, "source_backed_callout", parsed.get("callout"))
        question_payload = parsed.get("question_bank")
        if isinstance(question_payload, dict):
            existing = next((block for block in blocks if block.block_id == "question_bank"), None)
            if existing:
                existing_questions = existing.payload.get("questions", [])
                refs = [
                    item.get("source_ref")
                    for item in existing_questions
                    if isinstance(item, dict) and isinstance(item.get("source_ref"), dict)
                ]
                improved = []
                for index, item in enumerate(question_payload.get("questions", [])):
                    if not isinstance(item, dict):
                        continue
                    next_item = {
                        "label": clean(str(item.get("label", "")))[:48] or f"Q{index + 1}",
                        "question": clean(str(item.get("question", "")))[:220],
                        "answer": clean(str(item.get("answer", "")))[:500],
                    }
                    if index < len(refs):
                        next_item["source_ref"] = refs[index]
                    improved.append(next_item)
                if improved:
                    existing.payload["questions"] = improved
        return blocks

    def _merge_visual_payload(self, blocks: list[VisualInteractiveBlock], block_id: str, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        block = next((item for item in blocks if item.block_id == block_id), None)
        if not block:
            return
        block.payload.update(payload)

    def _document_context(self, extracted: ExtractedDocument, max_chars: int) -> str:
        chunks = []
        for frame in extracted.source_frames[:8]:
            chunks.append(f"[page {frame.index}] {clean(frame.text)[:1200]}")
        return "\n".join(chunks)[:max_chars]

    def _section_context(self, section: ReviewSection, extracted: ExtractedDocument, max_chars: int) -> str:
        frames = {frame.source_frame_id: frame for frame in extracted.source_frames}
        text = "\n".join(f"[page {frames[frame_id].index}] {frames[frame_id].text}" for frame_id in section.source_frame_ids if frame_id in frames)
        return clean(text)[:max_chars]

    def _claim_candidates(self, section: ReviewSection, extracted: ExtractedDocument) -> list[dict[str, Any]]:
        frames = {frame.source_frame_id: frame for frame in extracted.source_frames}
        candidates = []
        for frame_id in section.source_frame_ids:
            frame = frames.get(frame_id)
            if not frame:
                continue
            useful_units = [unit for unit in frame.units if len(clean(unit.text)) > 35]
            for unit in useful_units[:10]:
                candidates.append({"unit_id": unit.unit_id, "page": frame.index, "text": clean(unit.text)[:600]})
            if len(candidates) >= 18:
                break
        return candidates

    def _unit_lookup(self, extracted: ExtractedDocument) -> dict[str, tuple[SourceFrame, SourceUnit]]:
        return {unit.unit_id: (frame, unit) for frame in extracted.source_frames for unit in frame.units}
