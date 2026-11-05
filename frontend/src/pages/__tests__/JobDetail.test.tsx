import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import JobDetail from "@/pages/JobDetail";
import type { JobDetail as JobDetailData } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    health: vi.fn(),
    getJob: vi.fn(),
    retryJob: vi.fn(),
    cancelJob: vi.fn(),
  },
}));

const failed: JobDetailData = {
  job: {
    job_id: "job_failed",
    plugin: "news_carousel",
    topic: "A topic that broke the pipeline",
    angle: null,
    overrides: {},
    status: "FAILED",
    stage: "policy",
    progress: 0.6,
    error: {
      error_class: "InsufficientSourcesError",
      stage: "ingest",
      message: "Found 2 sources, need at least 3.",
      retryable: true,
    },
    seed: 7,
    recommended_plugin: null,
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    heartbeat_at: null,
  },
  stages: [
    { name: "spec", status: "completed", progress: 1 },
    { name: "ingest", status: "failed", progress: 0.5 },
    { name: "publish", status: "pending", progress: 0 },
  ],
  events_tail: [],
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/jobs/job_failed"]}>
        <Routes>
          <Route path="/jobs/:jobId" element={<JobDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.health).mockResolvedValue({ web: "ok", worker: { last_heartbeat: null, alive: true }, db: "ok" });
  vi.mocked(api.getJob).mockResolvedValue(failed);
  vi.mocked(api.retryJob).mockResolvedValue({ job_id: "job_retried" });
});

describe("JobDetail on a failed job", () => {
  it("names the typed failure and offers a retry", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("InsufficientSourcesError")).toBeInTheDocument();
    expect(screen.getByText("Found 2 sources, need at least 3.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /download logs/i })).toHaveAttribute(
      "href",
      "/api/jobs/job_failed/logs",
    );

    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(api.retryJob).toHaveBeenCalledWith("job_failed");
  });

  it("never calls a finished job 'waiting for the worker'", async () => {
    // Older rows carry no started_at; the copy must follow status, not the missing date.
    vi.mocked(api.getJob).mockResolvedValue({
      ...failed,
      job: { ...failed.job, status: "APPROVED", error: null, started_at: null, finished_at: new Date().toISOString() },
      stages: failed.stages.map((stage) => ({ ...stage, status: "completed" as const, progress: 1 })),
    });
    renderPage();

    expect(await screen.findByText(/created .* · finished/i)).toBeInTheDocument();
    expect(screen.queryByText(/waiting for the worker/i)).not.toBeInTheDocument();
  });

  it("marks the stage that failed", async () => {
    renderPage();
    const ingest = await screen.findByText("Ingest");
    expect(ingest.className).toContain("text-signal");
  });
});
