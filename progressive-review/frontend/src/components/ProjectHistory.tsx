import { Download, FolderOpen, RefreshCcw, Trash2, UploadCloud } from "lucide-react";
import { useEffect, useState } from "react";
import { deleteJob, exportHtmlUrl, listJobs, listProviders, uploadDocument } from "../api/client";
import { AgentProgress, formatStage, isActiveJob } from "./AgentProgress";
import type { JobSummary } from "../types/review";

type Props = {
  onOpenJob: (jobId: string) => void;
};

type ProviderOption = {
  id: string;
  label: string;
  configured: boolean;
  uses_ai: boolean;
};

function formatDate(value?: string): string {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function statusLabel(job: JobSummary): string {
  if (job.status === "complete" && job.valid === false) {
    return "complete with warnings";
  }
  return formatStage(job.stage ?? job.status);
}

function progressLabel(job: JobSummary): string {
  if (!job.progress?.total_blocks) {
    return "Waiting for workflow";
  }
  return `${job.progress.completed_blocks}/${job.progress.total_blocks} blocks`;
}

export function ProjectHistory({ onOpenJob }: Props) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [provider, setProvider] = useState("mock");
  const [providers, setProviders] = useState<ProviderOption[]>([{ id: "mock", label: "Mock", configured: true, uses_ai: false }]);

  const refresh = async () => {
    setError("");
    try {
      setJobs(await listJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load jobs");
    }
  };

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      if (cancelled) {
        return;
      }
      try {
        const providerData = await listProviders();
        if (!cancelled) {
          setProviders(providerData.providers);
          const selected = providerData.providers.find((item) => item.id === provider);
          if (!selected || !selected.configured) {
            setProvider(providerData.providers.find((item) => item.id === providerData.default && item.configured)?.id ?? "mock");
          }
        }
      } catch {
        // Job list remains usable even if the provider status endpoint is unavailable.
      }
      await refresh();
      if (!cancelled && jobs.some(isActiveJob)) {
        timer = window.setTimeout(tick, 2000);
      }
    };

    tick();

    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
    // The interval should react to the latest active/inactive set after each refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!jobs.some(isActiveJob)) {
      return;
    }
    const timer = window.setTimeout(refresh, 2000);
    return () => window.clearTimeout(timer);
  }, [jobs]);

  const onUpload = async (file?: File) => {
    if (!file) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await uploadDocument(file, provider);
      await refresh();
      onOpenJob(result.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (job: JobSummary) => {
    const ok = window.confirm(`Delete job ${job.title ?? job.job_id}? This removes generated pages and IR JSON.`);
    if (!ok) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await deleteJob(job.job_id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="history-screen">
      <header className="history-topbar">
        <div>
          <span className="kicker">Projects</span>
          <h1>Generation jobs</h1>
        </div>
        <div className="history-actions">
          <label className="provider-select">
            Agent
            <select value={provider} onChange={(event) => setProvider(event.target.value)} disabled={busy}>
              {providers.map((item) => (
                <option value={item.id} disabled={!item.configured} key={item.id}>
                  {item.label}
                  {item.uses_ai ? " AI" : ""}
                  {!item.configured ? " - key missing" : ""}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="secondary-button" onClick={refresh} disabled={busy}>
            <RefreshCcw size={16} aria-hidden />
            Refresh
          </button>
          <label className="primary-upload">
            <UploadCloud size={17} aria-hidden />
            {busy ? "Processing..." : "New PDF job"}
            <input type="file" accept="application/pdf,.pdf" disabled={busy} onChange={(event) => onUpload(event.target.files?.[0])} />
          </label>
        </div>
      </header>

      <main className="history-main">
        <section className="history-summary">
          <div>
            <span>{jobs.length}</span>
            <p>Total jobs</p>
          </div>
          <div>
            <span>{jobs.filter((job) => job.status === "complete").length}</span>
            <p>Completed</p>
          </div>
          <div>
            <span>{jobs.filter((job) => job.status === "failed").length}</span>
            <p>Failed</p>
          </div>
        </section>

        {error ? <p className="error">{error}</p> : null}

        {jobs.length ? (
          <section className="job-list" aria-label="Generation jobs">
            {jobs.map((job) => (
              <article className="job-card" key={job.job_id}>
                <div className="job-card__main">
                  <div>
                    <span className={`status-pill status-pill--${job.status}`}>{statusLabel(job)}</span>
                    <h2>{job.title ?? job.job_id}</h2>
                  </div>
                  <p className="job-meta">
                    {job.page_count ?? 0} pages · {job.claim_count ?? 0} claims · {progressLabel(job)} · Updated {formatDate(job.updated_at)}
                  </p>
                  {job.provider ? <p className="job-meta">Provider: {job.provider}</p> : null}
                  {job.progress?.total_blocks ? (
                    <AgentProgress job={job} compact />
                  ) : null}
                  {job.error ? <p className="error">{job.error}</p> : null}
                  {job.warnings?.length ? <p className="job-warning">{job.warnings.length} validation warning(s)</p> : null}
                </div>
                <div className="job-card__actions">
                  <button type="button" className="secondary-button" onClick={() => onOpenJob(job.job_id)} disabled={job.status === "failed"}>
                    <FolderOpen size={16} aria-hidden />
                    Open
                  </button>
                  {job.status === "complete" ? (
                    <a className="secondary-button" href={exportHtmlUrl(job.job_id)} target="_blank" rel="noreferrer">
                      <Download size={16} aria-hidden />
                      Export
                    </a>
                  ) : (
                    <button type="button" className="secondary-button" disabled>
                      <Download size={16} aria-hidden />
                      Export
                    </button>
                  )}
                  <button type="button" className="danger-button" onClick={() => onDelete(job)} disabled={busy}>
                    <Trash2 size={16} aria-hidden />
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </section>
        ) : (
          <section className="empty-history">
            <UploadCloud size={36} aria-hidden />
            <h2>No generation jobs yet</h2>
            <p>Upload a PDF to create the first source-linked review job.</p>
          </section>
        )}
      </main>
    </div>
  );
}
