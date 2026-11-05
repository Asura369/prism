import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { ArrowRight } from "lucide-react";
import { api } from "@/api/client";
import { PlateHeader } from "@/components/Plate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { PluginInfo } from "@/types";

const STARTERS = [
  "Why the ocean is still mostly unexplored",
  "How cities are redesigning for heat",
  "A daily habit that changes your sense of time",
];

function AngleSummary({ angle }: { angle: Record<string, unknown> }) {
  return (
    <div className="border border-ink-900/15 bg-paper-50 p-3.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="fac text-[9.5px]">Selected angle</span>
        {angle.recommended_plugin ? <Badge variant="outline">{String(angle.recommended_plugin)}</Badge> : null}
      </div>
      <p className="mt-2 text-[13.5px] font-semibold leading-snug text-ink-900">{String(angle.hook ?? "Chosen angle")}</p>
      {angle.framing ? <p className="mt-1 text-[12.5px] leading-relaxed text-ink-500">{String(angle.framing)}</p> : null}
      {angle.target_emotion ? (
        <p className="mt-2 text-[10.5px] uppercase tracking-[0.08em] text-ink-400">{String(angle.target_emotion)}</p>
      ) : null}
    </div>
  );
}

export default function NewJob() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const pluginsQuery = useQuery({ queryKey: ["plugins"], queryFn: api.plugins });
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.settings });

  const queryPlugin = params.get("plugin") ?? "";
  const [plugin, setPlugin] = useState(queryPlugin);
  const [topic, setTopic] = useState(params.get("topic") ?? "");
  const [style, setStyle] = useState("cream");
  const [seed, setSeed] = useState("");
  const [error, setError] = useState<string | null>(null);

  const angle = useMemo<Record<string, unknown> | null>(() => {
    const raw = params.get("angle");
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      return typeof parsed === "object" && parsed !== null ? parsed : null;
    } catch {
      return null;
    }
  }, [params]);

  const plugins = useMemo(() => pluginsQuery.data ?? [], [pluginsQuery.data]);

  useEffect(() => {
    if (plugin) return;
    const preferred = plugins.find((p) => p.name === queryPlugin && p.available) ?? plugins.find((p) => p.available);
    if (preferred) setPlugin(preferred.name);
  }, [plugin, plugins, queryPlugin]);

  const styles = settingsQuery.data?.styles?.length ? settingsQuery.data.styles : ["cream"];

  const mutation = useMutation({
    mutationFn: () =>
      api.createJob({
        plugin,
        topic: topic.trim(),
        angle,
        recommended_plugin: angle?.recommended_plugin ? String(angle.recommended_plugin) : null,
        overrides: {
          ...(style ? { style } : {}),
          ...(seed.trim() ? { seed: Number(seed) } : {}),
        },
      }),
    onSuccess: (data) => navigate(`/jobs/${data.job_id}`),
    onError: (err: Error) => setError(err.message),
  });

  const selected = plugins.find((p) => p.name === plugin);
  const canSubmit = Boolean(plugin && topic.trim().length > 2 && selected?.available) && !mutation.isPending;

  function choosePlugin(next: PluginInfo) {
    if (!next.available) return;
    setPlugin(next.name);
  }

  return (
    <div className="flex flex-col gap-6">
      <PlateHeader
        title="Send a topic through the pipeline"
        meta="The plugin turns your topic into a slide spec, renders a 4:5 deck, writes caption and alt text, then holds it in review."
      />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-6">
          <section>
            <div className="mb-2.5 flex items-baseline justify-between gap-3">
              <h2 className="text-[13px] font-semibold text-ink-900">Format</h2>
              <span className="fac text-[9.5px]">01</span>
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              {plugins.map((item) => {
                const active = item.name === plugin;
                return (
                  <button
                    key={item.name}
                    type="button"
                    onClick={() => choosePlugin(item)}
                    disabled={!item.available}
                    className={cn(
                      "relative flex flex-col gap-1.5 overflow-hidden rounded-plate border p-3.5 pt-4 text-left transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60",
                      active
                        ? "border-ink-900 bg-paper-50"
                        : "border-ink-900/12 bg-paper-50/60 hover:border-ink-900/35",
                      !item.available && "cursor-not-allowed opacity-45",
                    )}
                  >
                    <span
                      className={cn("absolute inset-x-0 top-0 h-[3px]", active ? "bg-ink-900" : "bg-transparent")}
                      aria-hidden
                    />
                    <span className="flex items-center justify-between gap-2">
                      <span className="text-[11.5px] font-semibold uppercase tracking-[0.09em] text-ink-900">
                        {item.name.replace("_carousel", "")}
                      </span>
                      {active ? <span className="fac text-[9px] text-ink-400">selected</span> : null}
                    </span>
                    <span className="text-[11.5px] leading-relaxed text-ink-500">{item.description}</span>
                    {!item.available ? (
                      <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[#a32d1b]">
                        Missing: {item.missing_adapters.join(", ")}
                      </span>
                    ) : null}
                  </button>
                );
              })}
              {!pluginsQuery.isLoading && plugins.length === 0 ? (
                <p className="text-[12.5px] text-ink-500">No plugins installed.</p>
              ) : null}
            </div>
          </section>

          <section>
            <div className="mb-2.5 flex items-baseline justify-between gap-3">
              <h2 className="text-[13px] font-semibold text-ink-900">Topic</h2>
              <span className="fac text-[9.5px]">02</span>
            </div>
            <Input
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="What should the deck be about?"
              maxLength={200}
              className="h-11 text-[14.5px]"
              aria-label="Topic"
            />
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5">
              {STARTERS.map((starter) => (
                <button
                  key={starter}
                  type="button"
                  onClick={() => setTopic(starter)}
                  className="text-left text-[11.5px] text-ink-500 underline decoration-ink-900/20 underline-offset-[3px] transition-colors hover:text-ink-900 hover:decoration-ink-900"
                >
                  {starter}
                </button>
              ))}
            </div>
          </section>

          {angle ? <AngleSummary angle={angle} /> : null}

          <details className="group rounded-plate border border-ink-900/12 bg-paper-50/60">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 text-[12px] font-semibold text-ink-700 transition-colors hover:text-ink-900">
              Advanced — style preset and seed
              <span className="text-[11px] text-ink-400 transition-transform group-open:rotate-90 motion-reduce:transition-none">›</span>
            </summary>
            <div className="grid gap-4 border-t border-ink-900/10 p-4 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5">
                <span className="label">Style preset</span>
                <select
                  value={style}
                  onChange={(event) => setStyle(event.target.value)}
                  className="h-9 rounded-field border border-ink-900/18 bg-paper-50 px-3 text-[13px] text-ink-900 transition-colors hover:border-ink-900/30 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60"
                >
                  {styles.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="label">Seed (optional)</span>
                <Input
                  value={seed}
                  onChange={(event) => setSeed(event.target.value.replace(/[^0-9]/g, ""))}
                  placeholder="Random"
                  inputMode="numeric"
                />
              </label>
            </div>
          </details>

          {error ? (
            <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">{error}</p>
          ) : null}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <Button size="lg" disabled={!canSubmit} onClick={() => mutation.mutate()}>
              {mutation.isPending ? "Queueing…" : "Run pipeline"}
              <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-[11.5px] text-ink-400">Jobs run one at a time in the local worker.</p>
          </div>
        </div>

        <aside className="rounded-plate border border-ink-900/12 bg-paper-50">
          <div className="border-b border-ink-900/10 px-4 py-3">
            <h2 className="text-[13px] font-semibold text-ink-900">What comes back</h2>
            <p className="mt-0.5 text-[11.5px] text-ink-500">A reviewable deck, not a published post.</p>
          </div>
          <div className="flex flex-col">
            {[
              ["5–10 PNG slides", "1080 × 1350, safe margins, no overflow."],
              ["Caption and alt text", "Hashtags per platform, alt text per slide."],
              ["Provenance manifest", "Adapters, prompts, hashes, and sources."],
            ].map(([title, body], index) => (
              <div key={title} className="flex gap-3 border-b border-ink-900/8 px-4 py-3 last:border-0">
                <span className="fac tnum shrink-0 pt-0.5 text-[9.5px]">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <p className="text-[12.5px] font-semibold text-ink-900">{title}</p>
                  <p className="mt-0.5 text-[11.5px] leading-relaxed text-ink-500">{body}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="border-t border-ink-900/10 px-4 py-3 text-[11px] leading-relaxed text-ink-400">
            No API key? The deterministic stub adapter runs the whole pipeline and marks the job degraded.
          </p>
        </aside>
      </div>
    </div>
  );
}
