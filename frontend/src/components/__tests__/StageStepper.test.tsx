import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StageStepper } from "@/components/StageStepper";
import type { Stage } from "@/types";

describe("StageStepper", () => {
  it("renders every stage and marks completed, running, and pending states", () => {
    const stages: Stage[] = [
      { name: "spec", status: "completed", progress: 1 },
      { name: "render", status: "running", progress: 0.4 },
      { name: "publish", status: "pending", progress: 0 },
    ];
    render(<StageStepper stages={stages} />);
    expect(screen.getByText("Spec")).toBeInTheDocument();
    expect(screen.getByText("Render")).toBeInTheDocument();
    expect(screen.getByText("Publish")).toBeInTheDocument();
    expect(screen.getByText("Render").className).toContain("text-ink-900");
  });
});
