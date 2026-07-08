import { ChevronLeft, ChevronRight, LocateFixed } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { frameImageUrl } from "../api/client";
import type { AgentLayoutSpec, BBox, SourceFrame, SourceRef, SourceUnit, VisualInteractiveBlock } from "../types/review";
import { VisualBlockGroup } from "./VisualBlockRenderer";

type Props = {
  jobId: string;
  frames: SourceFrame[];
  linkedSourceRefs: SourceRef[];
  visualBlocks?: VisualInteractiveBlock[];
  layoutSpec?: AgentLayoutSpec | null;
  selectedRef?: SourceRef | null;
  visibleGeneratedSourceRef?: SourceRef | null;
  onSyncToGeneratedPosition: () => void;
  onGeneratedSourceSelect: (sourceRef: SourceRef) => void;
  onSourceDocumentSelect: (sourceRef: SourceRef) => void;
};

function scaleBBox(bbox: BBox, frame?: SourceFrame): CSSProperties {
  if (!frame?.width || !frame?.height) {
    return {};
  }
  const [x0, y0, x1, y1] = bbox;
  return {
    left: `${(x0 / frame.width) * 100}%`,
    top: `${(y0 / frame.height) * 100}%`,
    width: `${((x1 - x0) / frame.width) * 100}%`,
    height: `${((y1 - y0) / frame.height) * 100}%`,
  };
}

function sameUnit(ref: SourceRef | null | undefined, frame: SourceFrame, unit: SourceUnit): boolean {
  if (!ref) {
    return false;
  }
  return ref.source_frame_id === frame.source_frame_id && ref.source_unit_id === unit.unit_id;
}

function bboxKey(frameId: string, bbox?: BBox | null): string | null {
  if (!bbox) {
    return null;
  }
  return `${frameId}:${bbox.map((value) => value.toFixed(2)).join(",")}`;
}

export function SourceViewer({
  jobId,
  frames,
  linkedSourceRefs,
  visualBlocks = [],
  layoutSpec,
  selectedRef,
  visibleGeneratedSourceRef,
  onSyncToGeneratedPosition,
  onGeneratedSourceSelect,
  onSourceDocumentSelect,
}: Props) {
  const pageRefs = useRef(new Map<string, HTMLElement>());
  const unitRefs = useRef(new Map<string, HTMLButtonElement>());
  const viewerRef = useRef<HTMLElement | null>(null);
  const suppressNextScrollRef = useRef(false);
  const [visibleFrameId, setVisibleFrameId] = useState<string>(() => frames[0]?.source_frame_id ?? "");
  const selectedFrameId = visibleFrameId || selectedRef?.source_frame_id || frames[0]?.source_frame_id;
  const currentIndex = Math.max(0, frames.findIndex((frame) => frame.source_frame_id === selectedFrameId));
  const frame = frames[currentIndex] ?? frames[0];
  const currentPageLabel = useMemo(() => (frame ? `Page ${frame.index}` : "No pages"), [frame]);
  const linkedUnitIds = useMemo(() => {
    return new Set(linkedSourceRefs.map((ref) => ref.source_unit_id).filter(Boolean) as string[]);
  }, [linkedSourceRefs]);
  const linkedBBoxKeys = useMemo(() => {
    return new Set(
      linkedSourceRefs
        .map((ref) => bboxKey(ref.source_frame_id, ref.bbox))
        .filter(Boolean) as string[],
    );
  }, [linkedSourceRefs]);

  useEffect(() => {
    if (!selectedRef) {
      return;
    }
    setVisibleFrameId(selectedRef.source_frame_id);
    if (suppressNextScrollRef.current) {
      suppressNextScrollRef.current = false;
      return;
    }
    const unitEl = selectedRef.source_unit_id ? unitRefs.current.get(selectedRef.source_unit_id) : undefined;
    const pageEl = pageRefs.current.get(selectedRef.source_frame_id);
    const target = unitEl ?? pageEl;
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [selectedRef]);

  const onScroll = () => {
    const viewer = viewerRef.current;
    if (!viewer) {
      return;
    }
    const viewerTop = viewer.getBoundingClientRect().top;
    let closestFrameId = visibleFrameId;
    let closestDistance = Number.POSITIVE_INFINITY;
    for (const [frameId, node] of pageRefs.current.entries()) {
      const distance = Math.abs(node.getBoundingClientRect().top - viewerTop - 52);
      if (distance < closestDistance) {
        closestDistance = distance;
        closestFrameId = frameId;
      }
    }
    if (closestFrameId && closestFrameId !== visibleFrameId) {
      setVisibleFrameId(closestFrameId);
    }
  };

  const selectFromSourceDocument = (sourceRef: SourceRef) => {
    suppressNextScrollRef.current = true;
    onSourceDocumentSelect(sourceRef);
  };

  const sourceUnitClassName = (sourceFrame: SourceFrame, unit: SourceUnit) => {
    const isLinked = linkedUnitIds.has(unit.unit_id) || linkedBBoxKeys.has(bboxKey(sourceFrame.source_frame_id, unit.bbox) ?? "");
    return [
      "source-unit",
      isLinked ? "source-unit--linked" : "source-unit--unlinked",
      sameUnit(selectedRef, sourceFrame, unit) ? "source-unit--active" : "",
    ]
      .filter(Boolean)
      .join(" ");
  };

  const go = (offset: number) => {
    const next = frames[currentIndex + offset];
    if (next) {
      onGeneratedSourceSelect({ source_frame_id: next.source_frame_id, page_index: next.index });
    }
  };

  if (!frame) {
    return <aside className="source-viewer empty">No source pages</aside>;
  }

  return (
    <aside className="source-viewer" ref={viewerRef} onScroll={onScroll}>
      <div className="source-viewer__bar">
        <button type="button" onClick={() => go(-1)} disabled={currentIndex <= 0} title="Previous page">
          <ChevronLeft size={18} aria-hidden />
        </button>
        <span>{currentPageLabel}</span>
        <button type="button" onClick={() => go(1)} disabled={currentIndex >= frames.length - 1} title="Next page">
          <ChevronRight size={18} aria-hidden />
        </button>
        <button
          type="button"
          className="source-sync-button"
          onClick={onSyncToGeneratedPosition}
          disabled={!visibleGeneratedSourceRef}
          title="Scroll original to current generated position"
        >
          <LocateFixed size={16} aria-hidden />
          <span>Sync</span>
        </button>
        <span className="source-status-key" aria-label="Source link status">
          <span className="source-status-key__item source-status-key__item--linked">Linked</span>
          <span className="source-status-key__item source-status-key__item--unlinked">Not linked</span>
        </span>
      </div>
      <div className="source-scroll">
        <VisualBlockGroup
          blocks={visualBlocks}
          placement="source_rail"
          layoutSpec={layoutSpec}
          onSourceSelect={onGeneratedSourceSelect}
          selectedGeneratedId={null}
        />
        {frames.map((sourceFrame) => (
          <section
            className="source-page"
            key={sourceFrame.source_frame_id}
            ref={(node) => {
              if (node) {
                pageRefs.current.set(sourceFrame.source_frame_id, node);
              } else {
                pageRefs.current.delete(sourceFrame.source_frame_id);
              }
            }}
          >
            <div className="source-page__label">Page {sourceFrame.index}</div>
            <div
              className="page-stage"
              onClick={() => {
                selectFromSourceDocument({
                  source_frame_id: sourceFrame.source_frame_id,
                  page_index: sourceFrame.index,
                });
              }}
            >
              <img src={frameImageUrl(jobId, sourceFrame.source_frame_id)} alt={`PDF page ${sourceFrame.index}`} />
              {sourceFrame.units
                .filter((unit) => unit.bbox)
                .map((unit) => (
                  <button
                    key={unit.unit_id}
                    type="button"
                    ref={(node) => {
                      if (node) {
                        unitRefs.current.set(unit.unit_id, node);
                      } else {
                        unitRefs.current.delete(unit.unit_id);
                      }
                    }}
                    className={sourceUnitClassName(sourceFrame, unit)}
                    style={scaleBBox(unit.bbox!, sourceFrame)}
                    title={unit.text}
                    onClick={(event) => {
                      event.stopPropagation();
                      selectFromSourceDocument({
                        source_frame_id: sourceFrame.source_frame_id,
                        source_unit_id: unit.unit_id,
                        page_index: sourceFrame.index,
                        bbox: unit.bbox,
                        quote: unit.text,
                      });
                    }}
                  >
                    <span>{unit.text}</span>
                  </button>
                ))}
              {selectedRef?.bbox && selectedRef.source_frame_id === sourceFrame.source_frame_id ? (
                <div className="bbox-highlight" style={scaleBBox(selectedRef.bbox, sourceFrame)} />
              ) : null}
            </div>
          </section>
        ))}
      </div>
      {selectedRef?.quote ? <p className="quote-preview">{selectedRef.quote}</p> : null}
    </aside>
  );
}
