import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MetadataForm } from "@/components/MetadataForm";
import type { ReviewMetadata } from "@/types";

const metadata: ReviewMetadata = {
  title: "Ocean facts",
  caption: "",
  hashtags: ["ocean"],
  platforms: ["instagram_feed"],
  ai_disclosure: true,
  alt_text: ["Slide one alt", "Slide two alt"],
};

describe("MetadataForm", () => {
  it("updates the caption counter and submits edits", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockImplementation(async (patch) => ({ ...metadata, ...patch }));
    render(<MetadataForm metadata={metadata} slideCount={2} onSave={onSave} />);

    expect(screen.getByText("0 / 2200")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Caption"), "Hello world");
    expect(screen.getByText("11 / 2200")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /save changes/i }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ caption: "Hello world", hashtags: ["ocean"], alt_text: metadata.alt_text }),
    );
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("adds hashtags without a leading hash and enforces the count", async () => {
    const user = userEvent.setup();
    render(<MetadataForm metadata={{ ...metadata, hashtags: [] }} slideCount={2} onSave={vi.fn()} />);
    const input = screen.getByLabelText("Add hashtag");
    await user.type(input, "#science{enter}");
    expect(screen.getByText("#science")).toBeInTheDocument();
    expect(screen.getByText("1 / 30")).toBeInTheDocument();
  });

  it("reports dirty state so review actions can wait for saves", async () => {
    const user = userEvent.setup();
    const onDirtyChange = vi.fn();
    render(
      <MetadataForm metadata={metadata} slideCount={2} onSave={vi.fn()} onDirtyChange={onDirtyChange} />,
    );
    await user.type(screen.getByLabelText("Caption"), "x");
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
  });

  it("disables save when alt text is empty", async () => {
    const user = userEvent.setup();
    render(<MetadataForm metadata={{ ...metadata, alt_text: ["", "ok"] }} slideCount={2} onSave={vi.fn()} />);
    await user.type(screen.getByLabelText("Caption"), "x");
    expect(screen.getByRole("button", { name: /save changes/i })).toBeDisabled();
  });
});
