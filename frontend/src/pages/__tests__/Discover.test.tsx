import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import Discover from "@/pages/Discover";
import type { ScoredCandidate } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    settings: vi.fn(),
    trends: vi.fn(),
    manualIdea: vi.fn(),
    uploadTrends: vi.fn(),
  },
}));

const candidate: ScoredCandidate = {
  candidate: {
    id: "manual:test",
    title: "Manual topic",
    source: "manual",
    url: "",
    snippet: "",
    metrics: {},
    fetched_at: new Date().toISOString(),
    cluster_id: null,
  },
  score: {
    heuristic: 0.6,
    safety: 0.9,
    visual_potential: 0.8,
    angle_ability: 0.8,
    saturation: 0.2,
    combined: 0.8,
    reasoning: "Safe",
  },
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Discover />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Discover", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.settings).mockResolvedValue({
      config: {
        discovery: {
          sources: {
            google_news_rss: { enabled: true },
            hackernews: { enabled: true },
          },
        },
      },
      keys: { LLM_KEY: "SET" },
      adapters: {},
      styles: ["cream"],
      fake_adapters: true,
    });
    vi.mocked(api.trends).mockResolvedValue({
      fetched_at: new Date().toISOString(),
      sources_used: [],
      sources_failed: [],
      candidates: [],
    });
    vi.mocked(api.manualIdea).mockResolvedValue({
      candidate_id: "manual:test",
      score: candidate.score,
      candidate,
    });
  });

  it("shows a manual candidate even when every fetchable source is toggled off", async () => {
    const user = userEvent.setup();
    renderPage();

    const google = await screen.findByRole("button", { name: "Google News" });
    const hn = screen.getByRole("button", { name: "Hacker News" });
    await user.click(google);
    await user.click(hn);

    await user.type(screen.getByPlaceholderText("Topic title"), "Manual topic");
    await user.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(screen.getByText("Manual topic")).toBeInTheDocument());
    expect(api.manualIdea).toHaveBeenCalled();
  });
});
