import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import App from "@/App";
import type { JobDetail, ReviewDetail } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    health: vi.fn(),
    getJob: vi.fn(),
    getReview: vi.fn(),
    approve: vi.fn(),
    reject: vi.fn(),
    retryJob: vi.fn(),
    patchMetadata: vi.fn(),
  },
}));

const job = {
  job_id: "job_test",
  plugin: "facts_carousel",
  topic: "Test topic",
  angle: null,
  overrides: {},
  status: "REVIEW_READY" as const,
  stage: "publish",
  progress: 1,
  error: null,
  seed: 1,
  recommended_plugin: null,
  created_at: new Date().toISOString(),
  started_at: null,
  finished_at: null,
  heartbeat_at: null,
};

const review: ReviewDetail = {
  job,
  metadata: {
    title: "Test topic",
    caption: "A caption",
    hashtags: ["facts"],
    platforms: ["instagram_feed"],
    ai_disclosure: true,
    alt_text: ["Slide one", "Slide two"],
  },
  manifest: {},
  technical: { slide_count: 2, resolution: "1080x1350", style: "cream", total_size_bytes: 2048 },
  artifact_urls: {
    slides: ["/media/review/job_test/slides/01.png", "/media/review/job_test/slides/02.png"],
    thumbnail: "/media/review/job_test/thumbnail.png",
    download: "/api/review/job_test/download",
  },
};

const jobDetail: JobDetail = { job, stages: [], events_tail: [] };

function renderRoute(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.health).mockResolvedValue({ web: "ok", worker: { last_heartbeat: null, alive: true }, db: "ok" });
  vi.mocked(api.getReview).mockResolvedValue(review);
  vi.mocked(api.getJob).mockResolvedValue(jobDetail);
});

describe("route tree", () => {
  it("renders the review page for /review/:jobId", async () => {
    renderRoute("/review/job_test");
    expect(await screen.findByRole("button", { name: /Approve/i })).toBeInTheDocument();
  });

  it("redirects a REVIEW_READY /jobs/:jobId to its review page", async () => {
    renderRoute("/jobs/job_test");
    expect(await screen.findByRole("button", { name: /Approve/i })).toBeInTheDocument();
  });

  it("renders not-found for an unknown path", async () => {
    renderRoute("/nope");
    expect(await screen.findByText("Page not found.")).toBeInTheDocument();
  });
});
