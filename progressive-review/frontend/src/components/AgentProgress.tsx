import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import type { JobSummary, ReviewBlockStatus, WorkflowProgress } from "../types/review";

type Props = {
  job?: JobSummary | null;
  blockStatuses?: ReviewBlockStatus[];
  compact?: boolean;
};

const terminalStatuses = new Set(["complete", "failed", "invalid", "unknown"]);

export function isActiveJob(job: JobSummary): boolean {
  return !terminalStatuses.has(job.status);
}

export function formatStage(value?: string): string {
  if (!value) {
    return "Waiting";
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function progressPercent(progress?: WorkflowProgress): number {
  if (!progress?.total_blocks) {
    return 0;
  }
  return Math.min(100, Math.round((progress.completed_blocks / progress.total_blocks) * 100));
}

function statusFromBlocks(blockStatuses: ReviewBlockStatus[] = []) {
  const complete = blockStatuses.filter((block) => block.status === "complete").length;
  const running = blockStatuses.filter((block) => block.status === "running").length;
  const failed = blockStatuses.filter((block) => block.status === "failed").length;
  const queued = Math.max(0, blockStatuses.length - complete - running - failed);
  return { complete, running, failed, queued };
}

function currentBlock(job?: JobSummary | null, blockStatuses: ReviewBlockStatus[] = []) {
  if (job?.current_block_id) {
    return blockStatuses.find((block) => block.block_id === job.current_block_id) ?? null;
  }
  return blockStatuses.find((block) => block.status === "running") ?? null;
}

export function AgentProgress({ job, blockStatuses = [], compact = false }: Props) {
  const counts = statusFromBlocks(blockStatuses);
  const stage = job?.stage ?? job?.status ?? "waiting";
  const progress = job?.progress ?? {
    completed_blocks: counts.complete,
    total_blocks: blockStatuses.length,
  };
  const percent = progressPercent(progress);
  const active = job ? isActiveJob(job) : blockStatuses.some((block) => block.status === "running" || block.status === "queued");
  const failed = job?.status === "failed" || counts.failed > 0;
  const current = currentBlock(job, blockStatuses);

  return (
    <section className={compact ? "agent-progress agent-progress--compact" : "agent-progress"} aria-label="Agent workflow progress">
      <div className="agent-progress__header">
        <span className={`agent-progress__state agent-progress__state--${failed ? "failed" : active ? "active" : "complete"}`}>
          {failed ? <XCircle size={15} aria-hidden /> : active ? <Loader2 size={15} aria-hidden className="spin" /> : <CheckCircle2 size={15} aria-hidden />}
          {formatStage(stage)}
        </span>
        {job?.provider ? <span className="agent-progress__provider">{job.provider}</span> : null}
      </div>

      <div className="agent-progress__track" aria-label={`${percent}% complete`}>
        <span style={{ width: `${percent}%` }} />
      </div>

      <div className="agent-progress__meta">
        <span>
          {progress.completed_blocks}/{progress.total_blocks || blockStatuses.length || 0} blocks
        </span>
        {current ? <span>Now: {current.title}</span> : null}
      </div>

      {!compact && blockStatuses.length ? (
        <div className="agent-progress__counts">
          <span>
            <CheckCircle2 size={14} aria-hidden />
            {counts.complete} done
          </span>
          <span>
            <Loader2 size={14} aria-hidden className={counts.running ? "spin" : undefined} />
            {counts.running} running
          </span>
          <span>
            <CircleDashed size={14} aria-hidden />
            {counts.queued} queued
          </span>
          {counts.failed ? (
            <span className="agent-progress__failed">
              <XCircle size={14} aria-hidden />
              {counts.failed} failed
            </span>
          ) : null}
        </div>
      ) : null}

      {job?.error ? <p className="agent-progress__error">{job.error}</p> : null}
    </section>
  );
}
