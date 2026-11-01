import type {
  Health,
  JobDetail,
  JobEvent,
  JobSummary,
  PluginInfo,
  ReviewDetail,
  ReviewItem,
  ReviewMetadata,
  SettingsResponse,
} from "@/types";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: init?.body ? { "content-type": "application/json" } : undefined,
    ...init,
  });
  if (!response.ok) {
    let code = "http_error";
    let message = response.statusText;
    try {
      const body = await response.json();
      code = body.error ?? code;
      message = body.message ?? message;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(response.status, code, message);
  }
  return (await response.json()) as T;
}

export interface CreateJobInput {
  plugin: string;
  topic: string;
  angle?: Record<string, unknown> | null;
  recommended_plugin?: string | null;
  overrides?: Record<string, unknown>;
}

export const api = {
  health: () => request<Health>("/health"),
  plugins: () => request<PluginInfo[]>("/plugins"),
  settings: () => request<SettingsResponse>("/settings"),
  listJobs: (status?: string) =>
    request<{ items: JobSummary[]; total: number }>(
      `/jobs${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  getJob: (id: string) => request<JobDetail>(`/jobs/${id}`),
  events: (id: string, since = 0) => request<JobEvent[]>(`/jobs/${id}/events?since=${since}`),
  createJob: (input: CreateJobInput) =>
    request<{ job_id: string }>("/jobs", { method: "POST", body: JSON.stringify(input) }),
  cancelJob: (id: string) =>
    request<{ ok: boolean }>(`/jobs/${id}/cancel`, { method: "POST" }),
  retryJob: (id: string) =>
    request<{ job_id: string }>(`/jobs/${id}/retry`, { method: "POST" }),
  reviewQueue: (decision?: string) =>
    request<ReviewItem[]>(`/review${decision ? `?decision=${encodeURIComponent(decision)}` : ""}`),
  getReview: (id: string) => request<ReviewDetail>(`/review/${id}`),
  patchMetadata: (id: string, patch: Partial<ReviewMetadata>) =>
    request<{ metadata: ReviewMetadata }>(`/review/${id}/metadata`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  approve: (id: string) => request<{ ok: boolean }>(`/review/${id}/approve`, { method: "POST" }),
  reject: (id: string, reason: string) =>
    request<{ ok: boolean }>(`/review/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
};
