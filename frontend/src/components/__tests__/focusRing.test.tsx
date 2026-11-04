import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

describe("focus rings survive forced-colors mode", () => {
  it("uses outline-hidden so Windows High Contrast still paints focus", () => {
    expect(buttonVariants()).toContain("focus-visible:outline-hidden");
    expect(buttonVariants()).not.toContain("focus-visible:outline-none");

    const { container } = render(
      <>
        <Input aria-label="title" />
        <Textarea aria-label="caption" />
      </>,
    );
    const controls = Array.from(container.querySelectorAll("input, textarea"));
    expect(controls).toHaveLength(2);
    for (const control of controls) {
      expect(control.className).toContain("focus-visible:outline-hidden");
      expect(control.className).not.toContain("focus-visible:outline-none");
    }
  });
});
