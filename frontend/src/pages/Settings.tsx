import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { PlateHeader, SectionHeading } from "@/components/Plate";
import { Badge } from "@/components/ui/badge";
import { relativeTime } from "@/lib/utils";

const INTERFACES = ["llm", "cards", "export", "news"] as const;

export default function Settings() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });

  return (
    <div className="flex flex-col gap-6">
      <PlateHeader
        title="Resolved adapters"
        meta={
          <>
            Values come from <code className="font-mono text-[11.5px]">config.yaml</code> plus environment. Edit the file
            and restart to change them.
          </>
        }
      />

      {settings.isError ? <p className="text-[12.5px] text-[#a32d1b]">{(settings.error as Error).message}</p> : null}

      <div className="grid items-start gap-6 md:grid-cols-2">
        <section>
          <SectionHeading>Keys</SectionHeading>
          <div className="flex flex-col">
            {settings.data
              ? Object.entries(settings.data.keys).map(([name, state]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between gap-4 border-b border-ink-900/8 py-2 last:border-0"
                  >
                    <span className="font-mono text-[11.5px] text-ink-500">{name}</span>
                    <Badge variant={state === "SET" ? "success" : "outline"}>{state}</Badge>
                  </div>
                ))
              : null}
            {settings.data?.fake_adapters ? (
              <p className="mt-3 border border-spectrum-policy/35 bg-spectrum-policy/[0.07] px-3 py-2 text-[11.5px] text-[#7c4a12]">
                Fake adapters are on. Every LLM call uses the deterministic fake.
              </p>
            ) : null}
          </div>
        </section>

        <section>
          <SectionHeading>Worker</SectionHeading>
          <div className="flex flex-col">
            <div className="flex items-center justify-between gap-4 border-b border-ink-900/8 py-2">
              <span className="text-[12px] text-ink-400">Alive</span>
              <Badge variant={health.data?.worker.alive ? "success" : "danger"}>
                {health.data?.worker.alive ? "yes" : "no"}
              </Badge>
            </div>
            <div className="flex items-center justify-between gap-4 border-b border-ink-900/8 py-2">
              <span className="text-[12px] text-ink-400">Last heartbeat</span>
              <span className="tnum text-[12.5px] font-medium text-ink-900">
                {health.data?.worker.last_heartbeat ? relativeTime(health.data.worker.last_heartbeat) : "never"}
              </span>
            </div>
            <p className="mt-3 text-[11.5px] text-ink-400">
              Start it with <code className="font-mono text-[11px]">make worker</code>.
            </p>
          </div>
        </section>
      </div>

      {settings.data ? (
        <section>
          <SectionHeading aside="fallback order">Adapter chains</SectionHeading>
          <div className="rounded-plate border border-ink-900/12 bg-paper-50">
            {INTERFACES.map((iface) => {
              const chain = settings.data.adapters[iface] ?? [];
              return (
                <div
                  key={iface}
                  className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-ink-900/8 px-4 py-2.5 last:border-0"
                >
                  <span className="w-16 shrink-0 text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-400">
                    {iface}
                  </span>
                  {chain.length === 0 ? (
                    <span className="text-[11.5px] text-ink-400">none registered</span>
                  ) : (
                    chain.map((adapter, index) => (
                      <span key={adapter.name} className="flex items-center gap-2">
                        {index > 0 ? <span className="text-ink-300">→</span> : null}
                        <Badge variant={adapter.available ? "success" : "outline"}>{adapter.name}</Badge>
                      </span>
                    ))
                  )}
                </div>
              );
            })}
          </div>
          <p className="mt-3 max-w-[70ch] text-[11.5px] leading-relaxed text-ink-400">
            A missing key makes the chain fall through to <code className="font-mono text-[11px]">fake</code> and marks
            the job degraded rather than failing it.
          </p>
        </section>
      ) : null}
    </div>
  );
}
