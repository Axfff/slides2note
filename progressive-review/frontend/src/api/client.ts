import type { JobSummary, ProgressiveReviewIR } from "../types/review";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function uploadDocument(file: File, provider = "mock"): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("provider", provider);
  const response = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function listProviders(): Promise<{
  default: string;
  providers: Array<{ id: string; label: string; configured: boolean; uses_ai: boolean }>;
}> {
  const response = await fetch(`${API_BASE}/api/providers`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function getJob(jobId: string): Promise<JobSummary> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function getJobIR(jobId: string, allowPartial = true): Promise<ProgressiveReviewIR> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}/ir?allow_partial=${allowPartial ? "true" : "false"}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function listJobs(): Promise<JobSummary[]> {
  const response = await fetch(`${API_BASE}/api/jobs`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const data = (await response.json()) as { jobs: JobSummary[] };
  return data.jobs;
}

export async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
}

export function exportHtmlUrl(jobId: string): string {
  return `${API_BASE}/api/jobs/${jobId}/export/html`;
}

export function frameImageUrl(jobId: string, frameId: string): string {
  return `${API_BASE}/api/jobs/${jobId}/frames/${frameId}/image`;
}
