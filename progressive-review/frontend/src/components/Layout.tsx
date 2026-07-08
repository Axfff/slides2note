import type { DetailLevel, JobSummary, ProgressiveReviewIR, SourceRef } from "../types/review";
import { DetailLevelControl } from "./DetailLevelControl";
import { OutlineSidebar } from "./OutlineSidebar";
import { ReviewPanel } from "./ReviewPanel";
import { SourceViewer } from "./SourceViewer";
import { FolderKanban } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import type { CSSProperties, PointerEvent } from "react";
import { AgentProgress } from "./AgentProgress";

type Props = {
  jobId: string;
  ir: ProgressiveReviewIR;
  detailLevel: DetailLevel;
  selectedRef: SourceRef | null;
  selectedGeneratedId?: string | null;
  jobStatus?: JobSummary | null;
  onDetailLevelChange: (level: DetailLevel) => void;
  onGeneratedSourceSelect: (sourceRef: SourceRef) => void;
  onSourceDocumentSelect: (sourceRef: SourceRef) => void;
  onBackToJobs: () => void;
};

export function Layout({
  jobId,
  ir,
  detailLevel,
  selectedRef,
  selectedGeneratedId,
  jobStatus,
  onDetailLevelChange,
  onGeneratedSourceSelect,
  onSourceDocumentSelect,
  onBackToJobs,
}: Props) {
  const workspaceRef = useRef<HTMLDivElement | null>(null);
  const [sourcePaneWidth, setSourcePaneWidth] = useState(() => {
    const viewportWidth = typeof window === "undefined" ? 1200 : window.innerWidth;
    return Math.min(Math.max(Math.round(viewportWidth * 0.34), ir.layout_spec?.source_column_min_px ?? 360), 720);
  });
  const [visibleGeneratedSourceRef, setVisibleGeneratedSourceRef] = useState<SourceRef | null>(null);
  const linkedSourceRefs = useMemo(
    () => [
      ...ir.claims.flatMap((claim) => claim.source_refs),
      ...ir.evidence_cards.flatMap((evidence) => evidence.source_refs),
      ...(ir.visual_blocks ?? []).flatMap((block) => block.source_refs),
    ],
    [ir.claims, ir.evidence_cards, ir.visual_blocks],
  );
  const workspaceStyle = {
    "--source-pane-width": `${sourcePaneWidth}px`,
  } as CSSProperties;

  const startSourceResize = (event: PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    const workspace = workspaceRef.current;
    if (!workspace) {
      return;
    }
    const workspaceRect = workspace.getBoundingClientRect();
    const outlineWidth = workspace.querySelector(".outline")?.getBoundingClientRect().width ?? 0;
    const minSourceWidth = ir.layout_spec?.source_column_min_px ?? 360;
    const minReviewWidth = ir.layout_spec?.review_column_min_px ?? 460;
    const availableContentWidth = workspaceRect.width - outlineWidth - 10;
    const maxSourceWidth = Math.max(minSourceWidth, availableContentWidth - minReviewWidth);
    document.body.classList.add("is-resizing-source-pane");

    const resize = (moveEvent: globalThis.PointerEvent) => {
      const nextWidth = Math.round(workspaceRect.right - moveEvent.clientX);
      setSourcePaneWidth(Math.min(Math.max(nextWidth, minSourceWidth), maxSourceWidth));
    };
    const stop = () => {
      document.body.classList.remove("is-resizing-source-pane");
      window.removeEventListener("pointermove", resize);
      window.removeEventListener("pointerup", stop);
      window.removeEventListener("pointercancel", stop);
    };
    window.addEventListener("pointermove", resize);
    window.addEventListener("pointerup", stop);
    window.addEventListener("pointercancel", stop);
  };

  const syncSourceToGeneratedPosition = () => {
    if (visibleGeneratedSourceRef) {
      onGeneratedSourceSelect(visibleGeneratedSourceRef);
    }
  };

  return (
    <div className={`app-shell app-shell--${ir.layout_spec?.style_preset ?? "workspace"}`}>
      <header className="topbar">
        <div>
          <span className="kicker">Progressive Review</span>
          <h1>{ir.title}</h1>
          {jobStatus?.is_partial || ir.is_partial ? <AgentProgress job={jobStatus} blockStatuses={ir.block_statuses} compact /> : null}
        </div>
        <div className="topbar-actions">
          <button type="button" className="secondary-button" onClick={onBackToJobs}>
            <FolderKanban size={16} aria-hidden />
            Jobs
          </button>
          <DetailLevelControl value={detailLevel} onChange={onDetailLevelChange} />
        </div>
      </header>
      <div className="workspace" ref={workspaceRef} style={workspaceStyle}>
        <OutlineSidebar sections={ir.outline} />
        <ReviewPanel
          ir={ir}
          jobStatus={jobStatus}
          detailLevel={detailLevel}
          onSourceSelect={onGeneratedSourceSelect}
          onVisibleSourceRefChange={setVisibleGeneratedSourceRef}
          selectedGeneratedId={selectedGeneratedId}
        />
        <button
          type="button"
          className="pane-resizer"
          aria-label="Resize generated and original panes"
          title="Resize panes"
          onPointerDown={startSourceResize}
        />
        <SourceViewer
          jobId={jobId}
          frames={ir.source_frames}
          linkedSourceRefs={linkedSourceRefs}
          visualBlocks={ir.visual_blocks ?? []}
          layoutSpec={ir.layout_spec}
          selectedRef={selectedRef}
          visibleGeneratedSourceRef={visibleGeneratedSourceRef}
          onSyncToGeneratedPosition={syncSourceToGeneratedPosition}
          onGeneratedSourceSelect={onGeneratedSourceSelect}
          onSourceDocumentSelect={onSourceDocumentSelect}
        />
      </div>
    </div>
  );
}
