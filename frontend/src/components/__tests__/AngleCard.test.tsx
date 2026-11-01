import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AngleCard } from "@/components/AngleCard";
import type { DispatchAngle, PluginInfo } from "@/types";

const angle: DispatchAngle = {
  hook: "Your body has a second brain",
  framing: "Three fast facts that reframe how the gut works",
  target_emotion: "surprise",
  format_suggestion: "facts",
  est_slide_count: 7,
  why_it_works: "It promises a concrete reframe.",
  recommended_plugin: "facts_carousel",
  plugin_reasoning: "Best told as a short fact list.",
};

const plugins: PluginInfo[] = [
  {
    name: "facts_carousel",
    version: "0.1.0",
    description: "Facts",
    output_kind: "image_sequence",
    defaults: {},
    available: true,
    missing_adapters: [],
  },
  {
    name: "faq_carousel",
    version: "0.1.0",
    description: "FAQ",
    output_kind: "image_sequence",
    defaults: {},
    available: true,
    missing_adapters: [],
  },
];

describe("AngleCard", () => {
  it("lets the user override the plugin and choose the angle", async () => {
    const user = userEvent.setup();
    const onPluginChange = vi.fn();
    const onUse = vi.fn();
    render(
      <AngleCard
        angle={angle}
        index={0}
        plugins={plugins}
        selectedPlugin="facts_carousel"
        onPluginChange={onPluginChange}
        onUse={onUse}
      />,
    );
    await user.selectOptions(screen.getByLabelText("Plugin for angle 1"), "faq_carousel");
    expect(onPluginChange).toHaveBeenCalledWith("faq_carousel");
    await user.click(screen.getByRole("button", { name: /use this angle/i }));
    expect(onUse).toHaveBeenCalled();
  });
});
