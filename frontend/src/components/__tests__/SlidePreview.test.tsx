import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SlidePreview } from "@/components/SlidePreview";

describe("SlidePreview", () => {
  it("navigates with the arrow keys", () => {
    const onChange = vi.fn();
    render(<SlidePreview slides={["/a.png", "/b.png", "/c.png"]} index={1} onChange={onChange} />);
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(onChange).toHaveBeenCalledWith(2);
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(onChange).toHaveBeenCalledWith(0);
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });
});
