import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ImageGallery } from "@/components/ImageGallery";

const slides = ["/a.png", "/b.png", "/c.png"];

describe("ImageGallery", () => {
  it("renders one thumbnail per slide and reports selection", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ImageGallery slides={slides} index={0} onSelect={onSelect} />);
    expect(screen.getAllByRole("option")).toHaveLength(3);
    await user.click(screen.getByLabelText("Slide 2"));
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
