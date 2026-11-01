import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { WorkerStatusBanner } from "@/components/WorkerStatusBanner";

vi.mock("@/api/client", () => ({ api: { health: vi.fn() } }));

function renderBanner() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WorkerStatusBanner />
    </QueryClientProvider>,
  );
}

describe("WorkerStatusBanner", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the make worker hint when the worker is down", async () => {
    vi.mocked(api.health).mockResolvedValue({ web: "ok", worker: { alive: false, last_heartbeat: null }, db: "ok" });
    renderBanner();
    await waitFor(() => expect(screen.getByText(/worker is not running/i)).toBeInTheDocument());
    expect(screen.getByText("make worker")).toBeInTheDocument();
  });

  it("stays hidden when the worker is alive", async () => {
    vi.mocked(api.health).mockResolvedValue({
      web: "ok",
      worker: { alive: true, last_heartbeat: new Date().toISOString() },
      db: "ok",
    });
    renderBanner();
    await waitFor(() => expect(api.health).toHaveBeenCalled());
    expect(screen.queryByText(/worker is not running/i)).not.toBeInTheDocument();
  });
});
