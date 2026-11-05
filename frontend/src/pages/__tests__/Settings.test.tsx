import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import Settings from "@/pages/Settings";
import type { ProviderInfo, SettingsResponse } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    settings: vi.fn(),
    providers: vi.fn(),
    health: vi.fn(),
    saveProvider: vi.fn(),
    deleteProviderKey: vi.fn(),
    activateProvider: vi.fn(),
    testProvider: vi.fn(),
  },
}));

const settings: SettingsResponse = {
  config: {},
  llm: { provider: "opencode_go", model: "deepseek-v4.1-flash", base_url: "https://gw/v1", key_set: true },
  adapters: { llm: [{ name: "opencode_go", available: true }] },
  styles: ["slate"],
  fake_adapters: false,
};

function provider(overrides: Partial<ProviderInfo>): ProviderInfo {
  return {
    name: "openai",
    label: "OpenAI",
    models: ["gpt-6-luna"],
    default_model: "gpt-6-luna",
    json_mode: true,
    base_url: "https://api.openai.com/v1",
    model: "gpt-6-luna",
    configured: false,
    key_set: false,
    active: false,
    ...overrides,
  };
}

const unset = [
  provider({ name: "deepseek", label: "DeepSeek", base_url: "https://api.deepseek.com", model: "deepseek-flash" }),
  provider({}),
  provider({
    name: "opencode_go",
    label: "OpenCode Go",
    base_url: "https://opencode.ai/inference/go/openai/v1",
    model: "deepseek-v4.1-flash",
  }),
];

const active = provider({
  name: "opencode_go",
  label: "OpenCode Go",
  base_url: "https://opencode.ai/inference/go/openai/v1",
  model: "deepseek-v4.1-flash",
  configured: true,
  key_set: true,
  active: true,
});

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Settings />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.settings).mockResolvedValue(settings);
  vi.mocked(api.providers).mockResolvedValue(unset);
  vi.mocked(api.health).mockResolvedValue({ web: "ok", worker: { alive: true, last_heartbeat: null }, db: "ok" });
  vi.mocked(api.deleteProviderKey).mockResolvedValue(unset[0]);
});

describe("Settings — model providers", () => {
  it("hides the provider forms behind a picker until one is chosen", async () => {
    renderPage();

    const trigger = await screen.findByRole("button", { name: "Choose a provider" });
    expect(screen.queryByLabelText("OpenAI API key")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("DeepSeek API key")).not.toBeInTheDocument();

    await userEvent.click(trigger);
    expect(screen.getAllByRole("option")).toHaveLength(3);

    await userEvent.click(screen.getByRole("option", { name: /OpenAI/ }));
    expect(await screen.findByLabelText("OpenAI API key")).toBeInTheDocument();
    expect(screen.queryByLabelText("DeepSeek API key")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("OpenCode Go API key")).not.toBeInTheDocument();
  });

  it("shows only the configured provider, with its preset read-only", async () => {
    vi.mocked(api.providers).mockResolvedValue([unset[0], unset[1], active]);
    renderPage();

    expect(await screen.findByText("https://opencode.ai/inference/go/openai/v1")).toBeInTheDocument();
    expect(screen.getAllByText("deepseek-v4.1-flash").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Choose a provider" })).not.toBeInTheDocument();
    expect(screen.queryByText("https://api.deepseek.com")).not.toBeInTheDocument();
    expect(screen.queryByText("https://api.openai.com/v1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("OpenCode Go API key")).not.toBeInTheDocument();
    expect(document.querySelector("input")).toBeNull();
  });

  it("deletes a stored key after confirmation", async () => {
    vi.mocked(api.providers).mockResolvedValue([unset[0], unset[1], active]);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Delete key" }));
    await waitFor(() => expect(api.deleteProviderKey).toHaveBeenCalledWith("opencode_go"));
  });

  it("never renders a stored key value", async () => {
    vi.mocked(api.providers).mockResolvedValue([unset[0], unset[1], active]);
    renderPage();
    await screen.findByText("https://opencode.ai/inference/go/openai/v1");

    expect(document.querySelector('input[type="password"]')).toBeNull();
    const inputs = Array.from(document.querySelectorAll("input"));
    expect(inputs.some((input) => input.value.startsWith("sk-"))).toBe(false);
  });
});
