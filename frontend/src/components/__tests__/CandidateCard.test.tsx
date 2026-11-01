import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CandidateCard } from "@/components/CandidateCard";
import type { ScoredCandidate } from "@/types";

const item: ScoredCandidate = {
  candidate: {
    id: "gn:test",
    title: "Why the ocean is still mostly unexplored",
    source: "google_news_rss",
    url: "https://example.com/ocean",
    snippet: "Most of the sea floor has never been mapped.",
    metrics: { recency_h: 2, cluster_size: 3 },
    fetched_at: new Date().toISOString(),
    cluster_id: "c:1",
  },
  score: {
    heuristic: 0.6,
    safety: 0.9,
    visual_potential: 0.8,
    angle_ability: 0.8,
    saturation: 0.2,
    combined: 0.88,
    reasoning: "Safe and easy to distill.",
  },
};

describe("CandidateCard", () => {
  it("renders the score and links to angles", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CandidateCard item={item} rank={1} />
      </MemoryRouter>,
    );
    expect(screen.getByText(item.candidate.title)).toBeInTheDocument();
    expect(screen.getByText("88")).toBeInTheDocument();
    expect(screen.getByText("3 sources")).toBeInTheDocument();
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/discover/angles?candidate_id=gn%3Atest");
    await user.click(link);
    expect(sessionStorage.getItem("prism:candidate:gn:test")).toContain("ocean");
  });
});
