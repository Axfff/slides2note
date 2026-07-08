import { useEffect, useState } from "react";
import { getJob, getJobIR } from "./api/client";
import { Layout } from "./components/Layout";
import { ProjectHistory } from "./components/ProjectHistory";
import type { DetailLevel, JobSummary, ProgressiveReviewIR, SourceRef } from "./types/review";

function App() {
  const [jobId, setJobId] = useState<string>(() => new URLSearchParams(window.location.search).get("job") ?? "");
  const [ir, setIr] = useState<ProgressiveReviewIR | null>(null);
  const [detailLevel, setDetailLevel] = useState<DetailLevel>("standard");
  const [selectedRef, setSelectedRef] = useState<SourceRef | null>(null);
  const [selectedGeneratedId, setSelectedGeneratedId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobSummary | null>(null);
  const [error, setError] = useState<string>("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!jobId) {
      setIr(null);
      return;
    }
    let cancelled = false;
    let timer: number | undefined;
    setBusy(true);
    setError("");
    window.history.replaceState(null, "", `?job=${jobId}`);

    const poll = async () => {
      try {
        const status = await getJob(jobId);
        if (cancelled) {
          return;
        }
        setJobStatus(status);
        try {
          const loaded = await getJobIR(jobId, true);
          if (cancelled) {
            return;
          }
          setIr(loaded);
          setSelectedRef((current) => current ?? { source_frame_id: loaded.source_frames[0]?.source_frame_id ?? "page_1", page_index: 1 });
          setSelectedGeneratedId((current) => current ?? "overview");
          setBusy(false);
          if (loaded.is_partial || !["complete", "failed"].includes(status.status)) {
            timer = window.setTimeout(poll, 1500);
          }
        } catch (irErr) {
          if (status.status === "failed" || status.status === "complete") {
            setError(status.error ?? (irErr instanceof Error ? irErr.message : "Job failed before IR was created"));
            setBusy(false);
          } else {
            timer = window.setTimeout(poll, 1500);
          }
        }
      } catch (statusErr) {
        if (!cancelled) {
          setError(statusErr instanceof Error ? statusErr.message : "Could not load job status");
          setBusy(false);
        }
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [jobId]);

  const openJob = (nextJobId: string) => {
    setError("");
    setIr(null);
    setJobId(nextJobId);
  };

  const backToJobs = () => {
    setJobId("");
    setIr(null);
    setSelectedRef(null);
    setSelectedGeneratedId(null);
    setJobStatus(null);
    window.history.replaceState(null, "", window.location.pathname);
  };

  const sameBBox = (left?: SourceRef["bbox"], right?: SourceRef["bbox"]): boolean => {
    if (!left || !right) {
      return false;
    }
    return left.every((value, index) => Math.abs(value - right[index]) < 0.01);
  };

  const findGeneratedTargetId = (sourceRef: SourceRef, pageFallback = true): string | null => {
    if (!ir) {
      return null;
    }
    const matchesRef = (candidate: SourceRef): boolean => {
      if (candidate.source_frame_id !== sourceRef.source_frame_id) {
        return false;
      }
      if (sourceRef.source_unit_id) {
        return sourceRef.source_unit_id === candidate.source_unit_id;
      }
      if (sourceRef.bbox) {
        return sameBBox(sourceRef.bbox, candidate.bbox);
      }
      return !candidate.source_unit_id && !candidate.bbox;
    };

    const claim = ir.claims.find((item) => item.source_refs.some(matchesRef));
    if (claim) {
      return `generated-${claim.claim_id}`;
    }
    const evidence = ir.evidence_cards.find((item) => item.source_refs.some(matchesRef));
    if (evidence) {
      return `generated-${evidence.evidence_id}`;
    }
    const visualBlock = (ir.visual_blocks ?? []).find((item) => item.source_refs.some(matchesRef));
    if (visualBlock) {
      return `generated-${visualBlock.block_id}`;
    }
    if (!pageFallback) {
      return null;
    }

    const sectionStack = [...ir.outline];
    while (sectionStack.length) {
      const section = sectionStack.shift()!;
      if (section.source_frame_ids.includes(sourceRef.source_frame_id)) {
        return section.section_id;
      }
      sectionStack.push(...section.children);
    }
    return "overview";
  };

  const scrollGeneratedIntoView = (targetId: string | null) => {
    if (!targetId) {
      return;
    }
    window.requestAnimationFrame(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  };

  const handleGeneratedSourceSelect = (sourceRef: SourceRef) => {
    setSelectedRef(sourceRef);
    setSelectedGeneratedId(findGeneratedTargetId(sourceRef));
  };

  const handleSourceDocumentSelect = (sourceRef: SourceRef) => {
    setSelectedRef(sourceRef);
    const targetId = sourceRef.source_unit_id || sourceRef.bbox ? findGeneratedTargetId(sourceRef, false) : null;
    if (targetId?.startsWith("generated-") && (detailLevel === "map" || detailLevel === "brief")) {
      setDetailLevel("standard");
    }
    setSelectedGeneratedId(targetId);
    window.setTimeout(() => scrollGeneratedIntoView(targetId), 50);
  };

  if (ir && jobId) {
    return (
      <Layout
        jobId={jobId}
        ir={ir}
        detailLevel={detailLevel}
        selectedRef={selectedRef}
        selectedGeneratedId={selectedGeneratedId}
        jobStatus={jobStatus}
        onDetailLevelChange={setDetailLevel}
        onGeneratedSourceSelect={handleGeneratedSourceSelect}
        onSourceDocumentSelect={handleSourceDocumentSelect}
        onBackToJobs={backToJobs}
      />
    );
  }

  if (jobId && busy) {
    return (
      <div className="loading-screen">
        <span className="kicker">{jobStatus?.stage ?? "Opening job"}</span>
        <h1>Loading source-linked review</h1>
        {jobStatus?.progress?.total_blocks ? (
          <p>{jobStatus.progress.completed_blocks}/{jobStatus.progress.total_blocks} blocks complete</p>
        ) : null}
      </div>
    );
  }

  if (jobId && error) {
    return (
      <div className="loading-screen">
        <span className="kicker">Job error</span>
        <h1>Could not open this job</h1>
        <p className="error">{error}</p>
        <button type="button" className="secondary-button" onClick={backToJobs}>
          Back to jobs
        </button>
      </div>
    );
  }

  return <ProjectHistory onOpenJob={openJob} />;
}

export default App;
