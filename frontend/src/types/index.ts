export type JobStatus =
  | "QUEUED"
  | "RUNNING"
  | "REVIEW_READY"
  | "APPROVED"
  | "REJECTED"
  | "FAILED"
  | "CANCELLED";

export interface JobSummary {
  job_id: string;
  plugin: string;
  topic: string;
  status: JobStatus;
  stage: string | null;
  progress: number;
  thumbnail_url: string | null;
  created_at: string;
}

export interface Job {
  job_id: string;
  plugin: string;
  topic: string;
  angle: Record<string, unknown> | null;
  overrides: Record<string, unknown>;
  status: JobStatus;
  stage: string | null;
  progress: number;
  error: {
    error_class: string;
    stage: string | null;
    message: string;
    retryable: boolean;
  } | null;
  seed: number;
  recommended_plugin: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  heartbeat_at: string | null;
}

export interface Stage {
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
}

export interface JobEvent {
  id: number;
  ts: string;
  stage: string | null;
  progress: number | null;
  level: string;
  message: string;
}

export interface JobDetail {
  job: Job;
  stages: Stage[];
  events_tail: JobEvent[];
}

export interface PluginInfo {
  name: string;
  version: string;
  description: string;
  output_kind: string;
  defaults: Record<string, unknown>;
  available: boolean;
  missing_adapters: string[];
  class_name?: string;
  manifest?: Record<string, unknown>;
}

export interface Health {
  web: string;
  worker: { last_heartbeat: string | null; alive: boolean };
  db: string;
}

export interface SettingsResponse {
  config: Record<string, unknown>;
  keys: { LLM_KEY: "SET" | "UNSET" };
  adapters: Record<string, { name: string; available: boolean }[]>;
  styles: string[];
  fake_adapters: boolean;
}

export interface ReviewMetadata {
  title: string;
  caption: string;
  hashtags: string[];
  platforms: string[];
  ai_disclosure: boolean;
  alt_text: string[];
}

export interface ReviewItem extends JobSummary {
  title: string;
  caption: string;
  decision: string | null;
}

export interface ReviewDetail {
  job: Job;
  metadata: ReviewMetadata;
  manifest: Record<string, unknown>;
  technical: {
    slide_count: number;
    resolution: string;
    style: string;
    total_size_bytes: number;
  };
  artifact_urls: {
    slides: string[];
    thumbnail: string;
    download: string;
  };
}
