import { ChevronDown, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Claim, DetailLevel, EvidenceCard as EvidenceCardType, JobSummary, ProgressiveReviewIR, ReviewSection, SourceRef } from "../types/review";
import { AgentProgress } from "./AgentProgress";
import { EvidenceCard } from "./EvidenceCard";
import { MathText } from "./MathText";
import { SourceLink } from "./SourceLink";
import { VisualBlockGroup } from "./VisualBlockRenderer";

type Props = {
  ir: ProgressiveReviewIR;
  jobStatus?: JobSummary | null;
  detailLevel: DetailLevel;
  onSourceSelect: (sourceRef: SourceRef) => void;
  onVisibleSourceRefChange: (sourceRef: SourceRef | null) => void;
  selectedGeneratedId?: string | null;
};

const rank: Record<DetailLevel, number> = {
  map: 0,
  brief: 1,
  standard: 2,
  evidence: 3,
  full: 4,
};

function sourceRefAttributes(sourceRef?: SourceRef | null): Record<string, string | undefined> {
  if (!sourceRef) {
    return {};
  }
  return {
    "data-source-frame-id": sourceRef.source_frame_id,
    "data-source-unit-id": sourceRef.source_unit_id ?? undefined,
    "data-source-page-index": sourceRef.page_index == null ? undefined : String(sourceRef.page_index),
    "data-source-bbox": sourceRef.bbox?.join(","),
  };
}

function sourceRefFromElement(element: HTMLElement): SourceRef | null {
  const frameId = element.dataset.sourceFrameId;
  if (!frameId) {
    return null;
  }
  const pageIndex = element.dataset.sourcePageIndex ? Number(element.dataset.sourcePageIndex) : Number(frameId.replace("page_", ""));
  const bboxValues = element.dataset.sourceBbox?.split(",").map(Number);
  const bbox = bboxValues?.length === 4 && bboxValues.every(Number.isFinite) ? (bboxValues as SourceRef["bbox"]) : undefined;
  return {
    source_frame_id: frameId,
    source_unit_id: element.dataset.sourceUnitId,
    page_index: Number.isFinite(pageIndex) ? pageIndex : undefined,
    bbox,
  };
}

function sourceRefKey(sourceRef: SourceRef | null): string {
  if (!sourceRef) {
    return "";
  }
  return [sourceRef.source_frame_id, sourceRef.source_unit_id ?? "", sourceRef.bbox?.join(",") ?? ""].join(":");
}

export function ReviewPanel({ ir, jobStatus, detailLevel, onSourceSelect, onVisibleSourceRefChange, selectedGeneratedId }: Props) {
  const panelRef = useRef<HTMLElement | null>(null);
  const reportedVisibleSourceRefKey = useRef("");
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const claimsById = useMemo(() => new Map(ir.claims.map((claim) => [claim.claim_id, claim])), [ir.claims]);
  const evidenceByClaim = useMemo(() => {
    const grouped = new Map<string, EvidenceCardType[]>();
    for (const evidence of ir.evidence_cards) {
      grouped.set(evidence.claim_id, [...(grouped.get(evidence.claim_id) ?? []), evidence]);
    }
    return grouped;
  }, [ir.evidence_cards]);

  const toggle = (id: string) => {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const reportVisibleSourceRef = useCallback(() => {
    const panel = panelRef.current;
    if (!panel) {
      return;
    }
    const panelRect = panel.getBoundingClientRect();
    const targetTop = panelRect.top + 28;
    let closest: HTMLElement | null = null;
    let closestDistance = Number.POSITIVE_INFINITY;
    for (const element of Array.from(panel.querySelectorAll<HTMLElement>("[data-source-frame-id]"))) {
      const rect = element.getBoundingClientRect();
      if (rect.bottom < panelRect.top || rect.top > panelRect.bottom) {
        continue;
      }
      const distance = Math.abs(rect.top - targetTop);
      if (distance < closestDistance) {
        closestDistance = distance;
        closest = element;
      }
    }
    const sourceRef = closest ? sourceRefFromElement(closest) : null;
    const nextKey = sourceRefKey(sourceRef);
    if (nextKey !== reportedVisibleSourceRefKey.current) {
      reportedVisibleSourceRefKey.current = nextKey;
      onVisibleSourceRefChange(sourceRef);
    }
  }, [onVisibleSourceRefChange]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(reportVisibleSourceRef);
    return () => window.cancelAnimationFrame(frame);
  }, [detailLevel, ir, reportVisibleSourceRef]);

  return (
    <main className="review-panel" ref={panelRef} onScroll={reportVisibleSourceRef}>
      <VisualBlockGroup
        blocks={ir.visual_blocks ?? []}
        placement="hero"
        layoutSpec={ir.layout_spec}
        onSourceSelect={onSourceSelect}
        sourceRefAttributes={sourceRefAttributes}
        selectedGeneratedId={selectedGeneratedId}
      />
      {ir.is_partial || jobStatus?.is_partial ? (
        <>
          <AgentProgress job={jobStatus} blockStatuses={ir.block_statuses ?? []} />
          <BlockProgress blockStatuses={ir.block_statuses ?? []} currentBlockId={jobStatus?.current_block_id} />
        </>
      ) : null}
      {ir.validation?.warnings?.length ? (
        <div className="validation-warning">
          <strong>Validation warnings</strong>
          <ul>
            {ir.validation.warnings.slice(0, 5).map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {ir.outline.map((section) => (
        <SectionBlock
          key={section.section_id}
          ir={ir}
          section={section}
          detailLevel={detailLevel}
          claimsById={claimsById}
          evidenceByClaim={evidenceByClaim}
          collapsed={collapsed}
          onToggle={toggle}
          onSourceSelect={onSourceSelect}
          sourceRefAttributes={sourceRefAttributes}
          selectedGeneratedId={selectedGeneratedId}
        />
      ))}
      <VisualBlockGroup
        blocks={ir.visual_blocks ?? []}
        placement="after_sections"
        layoutSpec={ir.layout_spec}
        onSourceSelect={onSourceSelect}
        sourceRefAttributes={sourceRefAttributes}
        selectedGeneratedId={selectedGeneratedId}
      />
    </main>
  );
}

function BlockProgress({
  blockStatuses,
  currentBlockId,
}: {
  blockStatuses: NonNullable<ProgressiveReviewIR["block_statuses"]>;
  currentBlockId?: string | null;
}) {
  const pending = blockStatuses.filter((block) => block.status !== "complete");
  const completed = blockStatuses.length - pending.length;
  const current = blockStatuses.find((block) => block.block_id === currentBlockId) ?? blockStatuses.find((block) => block.status === "running");
  const nextBlocks = pending.filter((block) => block.block_id !== current?.block_id).slice(0, 6);
  if (!blockStatuses.length) {
    return (
      <div className="block-progress-panel">
        <strong>Preparing workflow</strong>
        <div className="skeleton-line" />
        <div className="skeleton-line short" />
      </div>
    );
  }
  return (
    <div className="block-progress-panel">
      <strong>{completed}/{blockStatuses.length} blocks complete</strong>
      {current ? (
        <div className={`block-placeholder block-placeholder--current block-placeholder--${current.status}`}>
          <span>{current.status}</span>
          <p>{current.title}</p>
        </div>
      ) : null}
      <div className="block-progress-list">
        {nextBlocks.map((block) => (
          <div className={`block-placeholder block-placeholder--${block.status}`} key={block.block_id}>
            <span>{block.status}</span>
            <p>{block.title}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

type SectionProps = {
  ir: ProgressiveReviewIR;
  section: ReviewSection;
  detailLevel: DetailLevel;
  claimsById: Map<string, Claim>;
  evidenceByClaim: Map<string, EvidenceCardType[]>;
  collapsed: Set<string>;
  onToggle: (id: string) => void;
  onSourceSelect: (sourceRef: SourceRef) => void;
  sourceRefAttributes: (sourceRef?: SourceRef | null) => Record<string, string | undefined>;
  selectedGeneratedId?: string | null;
};

function SectionBlock({
  ir,
  section,
  detailLevel,
  claimsById,
  evidenceByClaim,
  collapsed,
  onToggle,
  onSourceSelect,
  sourceRefAttributes,
  selectedGeneratedId,
}: SectionProps) {
  const isCollapsed = collapsed.has(section.section_id);
  const showBrief = rank[detailLevel] >= 1 || section.section_id === "overview";
  const showClaims = rank[detailLevel] >= 2;
  const showEvidence = rank[detailLevel] >= 3;
  const showFull = rank[detailLevel] >= 4;
  const claims = section.key_claim_ids.map((id) => claimsById.get(id)).filter(Boolean) as Claim[];
  const showRootVisuals = section.section_id === "overview";

  return (
    <section
      id={section.section_id}
      {...sourceRefAttributes(
        section.source_frame_ids[0] ? { source_frame_id: section.source_frame_ids[0], page_index: Number(section.source_frame_ids[0].replace("page_", "")) } : null,
      )}
      className={[
        section.section_id === "overview" ? "section overview" : "section",
        selectedGeneratedId === section.section_id ? "generated-active" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <button type="button" className="section-title" onClick={() => onToggle(section.section_id)}>
        {isCollapsed ? <ChevronRight size={18} /> : <ChevronDown size={18} />}
        <span>{section.title}</span>
      </button>
      {!isCollapsed ? (
        <div className="section-body">
          {showBrief ? <MathText as="p" text={section.summary} /> : null}
          {section.source_frame_ids.length ? (
            <div className="source-row">
              {section.source_frame_ids.map((frameId) => (
                <SourceLink
                  key={frameId}
                  sourceRef={{ source_frame_id: frameId, page_index: Number(frameId.replace("page_", "")) }}
                  onSelect={onSourceSelect}
                />
              ))}
            </div>
          ) : null}
          {showRootVisuals ? (
            <>
              <VisualBlockGroup
                blocks={ir.visual_blocks ?? []}
                placement="after_overview"
                layoutSpec={ir.layout_spec}
                onSourceSelect={onSourceSelect}
                sourceRefAttributes={sourceRefAttributes}
                selectedGeneratedId={selectedGeneratedId}
              />
              <VisualBlockGroup
                blocks={ir.visual_blocks ?? []}
                placement="before_sections"
                layoutSpec={ir.layout_spec}
                onSourceSelect={onSourceSelect}
                sourceRefAttributes={sourceRefAttributes}
                selectedGeneratedId={selectedGeneratedId}
              />
            </>
          ) : null}
          {showClaims && claims.length ? (
            <div className="claims">
              {claims.map((claim) => (
                <article
                  id={`generated-${claim.claim_id}`}
                  {...sourceRefAttributes(claim.source_refs[0])}
                  className={selectedGeneratedId === `generated-${claim.claim_id}` ? "claim generated-active" : "claim"}
                  key={claim.claim_id}
                  role={claim.source_refs[0] ? "button" : undefined}
                  tabIndex={claim.source_refs[0] ? 0 : undefined}
                  onClick={() => {
                    if (claim.source_refs[0]) {
                      onSourceSelect(claim.source_refs[0]);
                    }
                  }}
                  onKeyDown={(event) => {
                    if ((event.key === "Enter" || event.key === " ") && claim.source_refs[0]) {
                      event.preventDefault();
                      onSourceSelect(claim.source_refs[0]);
                    }
                  }}
                >
                  <div className="claim__top">
                    <MathText as="span" className="claim-title" text={claim.text} />
                    {claim.source_refs[0] ? <SourceLink sourceRef={claim.source_refs[0]} onSelect={onSourceSelect} /> : null}
                  </div>
                  {claim.explanation ? <MathText as="p" text={claim.explanation} /> : null}
                  {claim.tags.length ? (
                    <div className="tags">
                      {claim.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                  ) : null}
                  {showEvidence
                    ? (evidenceByClaim.get(claim.claim_id) ?? []).map((evidence) => (
                        <EvidenceCard
                          key={evidence.evidence_id}
                          evidence={evidence}
                          onSourceSelect={onSourceSelect}
                          sourceRefAttributes={sourceRefAttributes}
                          selectedGeneratedId={selectedGeneratedId}
                        />
                      ))
                    : null}
                </article>
              ))}
            </div>
          ) : null}
          {showFull && section.full_notes ? (
            <details className="full-notes" open>
              <summary>Full page notes</summary>
              <MathText as="pre" text={section.full_notes} />
            </details>
          ) : null}
          {section.children.length && detailLevel !== "map"
            ? section.children.map((child) => (
                <SectionBlock
                  key={child.section_id}
                  ir={ir}
                  section={child}
                  detailLevel={detailLevel}
                  claimsById={claimsById}
                  evidenceByClaim={evidenceByClaim}
                  collapsed={collapsed}
                  onToggle={onToggle}
                  onSourceSelect={onSourceSelect}
                  sourceRefAttributes={sourceRefAttributes}
                  selectedGeneratedId={selectedGeneratedId}
                />
              ))
            : null}
          {section.children.length && detailLevel === "map" ? (
            <ol className="structure-map">
              {section.children.map((child) => (
                <li key={child.section_id}>
                  <a href={`#${child.section_id}`}>{child.title}</a>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
