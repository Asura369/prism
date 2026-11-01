import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { relativeTime } from "@/lib/utils";

const INTERFACES = ["llm", "cards", "export", "news"] as const;

export default function Settings() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });

  return (
    <div className="flex flex-col gap-7">
      <div>
        <p className="eyebrow">Settings</p>
        <h1 className="page-title mt-2">Resolved adapters</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-500">
          Values come from <code className="font-mono text-xs">config.yaml</code> plus environment. Edit the file and
          restart to change them.
        </p>
      </div>

      {settings.isError && <p className="text-sm text-red-700">{(settings.error as Error).message}</p>}

      <div className="grid gap-5 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Keys</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {settings.data &&
              Object.entries(settings.data.keys).map(([name, state]) => (
                <div key={name} className="flex items-center justify-between gap-4">
                  <span className="font-mono text-xs text-ink-500">{name}</span>
                  <Badge variant={state === "SET" ? "success" : "outline"}>{state}</Badge>
                </div>
              ))}
            {settings.data?.fake_adapters && (
              <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                FAKE_ADAPTERS is on. Every LLM call uses the deterministic fake.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Worker</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <div className="flex items-center justify-between gap-4">
              <span className="text-ink-400">Alive</span>
              <Badge variant={health.data?.worker.alive ? "success" : "danger"}>
                {health.data?.worker.alive ? "yes" : "no"}
              </Badge>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-ink-400">Last heartbeat</span>
              <span>{health.data?.worker.last_heartbeat ? relativeTime(health.data.worker.last_heartbeat) : "never"}</span>
            </div>
            <p className="text-xs text-ink-400">
              Start it with <code className="font-mono">make worker</code>.
            </p>
          </CardContent>
        </Card>
      </div>

      {settings.data && (
        <Card>
          <CardHeader>
            <CardTitle>Adapter chains</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {INTERFACES.map((iface) => (
              <div key={iface} className="flex flex-wrap items-center gap-2">
                <span className="w-16 text-xs font-semibold uppercase tracking-wide text-ink-400">{iface}</span>
                {(settings.data.adapters[iface] ?? []).map((adapter) => (
                  <Badge key={adapter.name} variant={adapter.available ? "success" : "outline"}>
                    {adapter.name}
                  </Badge>
                ))}
                {(settings.data.adapters[iface] ?? []).length === 0 && (
                  <span className="text-xs text-ink-400">none registered</span>
                )}
              </div>
            ))}
            <p className="mt-2 text-xs text-ink-400">
              Missing keys make the chain fall through to <code className="font-mono">fake</code> and mark jobs degraded.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
