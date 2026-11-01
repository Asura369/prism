import type {
  DispatchAngle,
  DiscoverResponse,
  DraftJobPayload,
  Health,
  JobDetail,
  JobEvent,
  JobSummary,
  ManualIdeaResponse,
  PluginInfo,
  ReviewDetail,
  ReviewItem,
  ReviewMetadata,
  ScoredCandidate,
  SettingsResponse,
  UploadTrendsResponse,
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
  const isForm = init?.body instanceof FormData;
  const response = await fetch(`/api${path}`, {
    headers: init?.body && !isForm ? { "content-type": "application/json" } : undefined,
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
  trends: (params: { region: string; windowH: number; sources: string[] }) =>
    request<DiscoverResponse>(
      `/discover/trends?region=${encodeURIComponent(params.region)}&window_h=${params.windowH}&sources=${encodeURIComponent(
        params.sources.join(","),
      )}`,
    ),
  manualIdea: (body: { title: string; snippet?: string; url?: string }) =>
    request<ManualIdeaResponse>("/discover/manual", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  uploadTrends: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadTrendsResponse>("/discover/trends/upload", {
      method: "POST",
      body: form,
    });
  },
  angles: (candidateId: string) =>
    request<{ angles: DispatchAngle[]; candidate?: ScoredCandidate }>("/discover/angles", {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId }),
    }),
  selectAngle: (candidateId: string, angleIndex: number, plugin: string) =>
    request<{ draft_job_payload: DraftJobPayload }>("/discover/select", {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId, angle_index: angleIndex, plugin }),
    }),
};
