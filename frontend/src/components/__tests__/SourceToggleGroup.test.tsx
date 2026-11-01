import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SourceToggleGroup } from "@/components/SourceToggleGroup";

const sources = [
  { name: "google_news_rss", label: "Google News" },
  { name: "hackernews", label: "Hacker News" },
];

describe("SourceToggleGroup", () => {
  it("adds and removes sources", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SourceToggleGroup sources={sources} selected={["google_news_rss"]} onChange={onChange} />);
    expect(screen.getByRole("button", { name: "Google News" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "Hacker News" }));
    expect(onChange).toHaveBeenCalledWith(["google_news_rss", "hackernews"]);
    await user.click(screen.getByRole("button", { name: "Google News" }));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
