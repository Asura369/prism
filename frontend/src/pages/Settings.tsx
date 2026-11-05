import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { PlateHeader, SectionHeading } from "@/components/Plate";
import { ProviderCard } from "@/components/ProviderCard";
import { ProviderPicker } from "@/components/ProviderPicker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { relativeTime } from "@/lib/utils";

const INTERFACES = ["llm", "cards", "export", "news"] as const;

export default function Settings() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const providers = useQuery({ queryKey: ["providers"], queryFn: api.providers });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });

  const llm = settings.data?.llm;
  const [picked, setPicked] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const stubOnly = settings.data?.stub_only ?? false;
  const toggleStub = useMutation({
    mutationFn: (enabled: boolean) => api.setStubOnly(enabled),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["settings"] }),
        queryClient.invalidateQueries({ queryKey: ["providers"] }),
      ]);
    },
  });

  const providersList = providers.data ?? [];
  // Only one connection is ever visible: the active one, else any configured one.
  const configured =
    providersList.find((provider) => provider.active && provider.configured) ??
    providersList.find((provider) => provider.configured);
  const chosen = configured ?? providersList.find((provider) => provider.name === picked);

  return (
    <div className="flex flex-col gap-6">
      <PlateHeader
        title="Settings"
        meta={
          <>
            Providers are configured here and stored in the local database — the only place they live.
          </>
        }
      />

      {settings.isError ? <p className="text-[12.5px] text-[#a32d1b]">{(settings.error as Error).message}</p> : null}

      <section>
        <SectionHeading aside="write-only keys">Model providers</SectionHeading>
        <p className="mb-3 text-[11.5px] text-ink-400">
          {llm?.provider ? (
            <>
              Active: <span className="font-mono text-ink-700">{llm.provider}</span> ·{" "}
              <span className="font-mono text-ink-700">{llm.model}</span>
            </>
          ) : (
            <>No provider active. Jobs run on the deterministic stub until you set one up.</>
          )}
        </p>


        {providers.isError ? (
          <p className="text-[12.5px] text-[#a32d1b]">{(providers.error as Error).message}</p>
        ) : null}

        {providers.isSuccess && !providersList.length ? (
          <p className="text-[11.5px] text-ink-400">No provider manifests found.</p>
        ) : null}

        <div className="flex max-w-[560px] flex-col gap-3">
          {configured ? (
            <ProviderCard key={configured.name} provider={configured} />
          ) : (
            <>
              <div className="flex items-center gap-3">
                <ProviderPicker providers={providersList} selected={picked} onSelect={setPicked} />
                <span className="text-[11.5px] text-ink-400">
                  {picked ? "Enter a key to finish setting it up." : "Pick the provider you want to run jobs with."}
                </span>
              </div>
              {chosen ? <ProviderCard key={chosen.name} provider={chosen} /> : null}
            </>
          )}
        </div>
      </section>

      <section>
        <SectionHeading aside={stubOnly ? "on" : "off"}>Testing mode</SectionHeading>
        <div className="flex max-w-[560px] items-start justify-between gap-4 border border-ink-900/12 bg-paper-50 px-4 py-3">
          <p className="text-[11.5px] leading-relaxed text-ink-400">
            Run every job on canned stub data. Nothing reaches a provider, so no key is used and no tokens are spent.
            <br />
            <span className="text-ink-700">
              {stubOnly
                ? "On — provider settings below are ignored and jobs are marked degraded."
                : "Off — jobs use the active provider; stub output is marked degraded."}
            </span>
          </p>
          <Button
            size="sm"
            variant={stubOnly ? "outline" : "default"}
            disabled={toggleStub.isPending}
            onClick={() => toggleStub.mutate(!stubOnly)}
          >
            {stubOnly ? "Turn off" : "Turn on"}
          </Button>
        </div>
        {toggleStub.isError ? (
          <p className="mt-2 text-[12.5px] text-[#a32d1b]">{(toggleStub.error as Error).message}</p>
        ) : null}
      </section>

      <section>
        <SectionHeading>Worker</SectionHeading>
        <div className="flex max-w-[520px] flex-col">
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
            Start it with <code className="font-mono text-[11px]">make worker</code>. Provider changes land on the next
            job — no restart.
          </p>
        </div>
      </section>

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
            A missing key makes the chain fall through to <code className="font-mono text-[11px]">stub</code> and marks
            the job degraded rather than failing it.
          </p>
        </section>
      ) : null}
    </div>
  );
}
