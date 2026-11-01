import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="rounded-xl border border-ember-500/25 bg-ember-500/5 p-4">
      <p className="eyebrow text-ember-600">Selected angle</p>
      <p className="mt-2 text-sm font-semibold text-ink-900">{String(angle.hook ?? "Chosen angle")}</p>
      {angle.framing ? <p className="mt-1 text-sm leading-relaxed text-ink-500">{String(angle.framing)}</p> : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {angle.target_emotion ? <Badge variant="outline">{String(angle.target_emotion)}</Badge> : null}
        {angle.recommended_plugin ? <Badge variant="ember">{String(angle.recommended_plugin)}</Badge> : null}
      </div>
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
    <div className="flex flex-col gap-7">
      <div>
        <p className="eyebrow">New job</p>
        <h1 className="page-title mt-2">Send a topic through the pipeline</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-500">
          The plugin turns your topic into a slide spec, renders a 4:5 deck, writes caption and alt text,
          then holds it in review.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        <div className="flex flex-col gap-6">
          <section>
            <p className="eyebrow mb-3">1 · Format</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {plugins.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  onClick={() => choosePlugin(item)}
                  disabled={!item.available}
                  className={cn(
                    "rounded-card border p-4 text-left transition-colors",
                    item.name === plugin
                      ? "border-ink-900 bg-white"
                      : "border-ink-900/10 bg-white/50 hover:border-ink-900/30",
                    !item.available && "cursor-not-allowed opacity-50",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-bold text-ink-900">{item.name.replace("_carousel", "")}</span>
                    {item.name === plugin && <Check className="h-4 w-4 text-ember-600" />}
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-ink-500">{item.description}</p>
                  {!item.available && (
                    <p className="mt-2 text-[11px] font-semibold text-red-600">
                      Missing: {item.missing_adapters.join(", ")}
                    </p>
                  )}
                </button>
              ))}
              {!pluginsQuery.isLoading && plugins.length === 0 && (
                <p className="text-sm text-ink-500">No plugins installed.</p>
              )}
            </div>
          </section>

          <section>
            <p className="eyebrow mb-3">2 · Topic</p>
            <Input
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="What should the deck be about?"
              maxLength={200}
            />
            <div className="mt-3 flex flex-wrap gap-2">
              {STARTERS.map((starter) => (
                <button
                  key={starter}
                  type="button"
                  onClick={() => setTopic(starter)}
                  className="rounded-full border border-ink-900/10 bg-white/60 px-3 py-1 text-xs text-ink-500 transition-colors hover:border-ink-900/30 hover:text-ink-900"
                >
                  {starter}
                </button>
              ))}
            </div>
          </section>

          {angle ? <AngleSummary angle={angle} /> : null}

          <details className="rounded-card border border-ink-900/10 bg-white/50 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-ink-700">Advanced</summary>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-ink-500">
                Style preset
                <select
                  value={style}
                  onChange={(event) => setStyle(event.target.value)}
                  className="h-11 rounded-xl border border-ink-900/15 bg-white/80 px-3 text-sm font-normal text-ink-900"
                >
                  {styles.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-ink-500">
                Seed (optional)
                <Input
                  value={seed}
                  onChange={(event) => setSeed(event.target.value.replace(/[^0-9]/g, ""))}
                  placeholder="Random"
                  inputMode="numeric"
                />
              </label>
            </div>
          </details>

          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
          )}

          <div className="flex items-center gap-4">
            <Button size="lg" disabled={!canSubmit} onClick={() => mutation.mutate()}>
              {mutation.isPending ? "Queueing…" : "Run pipeline"}
              <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-xs text-ink-400">Jobs run one at a time in the local worker.</p>
          </div>
        </div>

        <Card className="h-fit">
          <CardHeader>
            <p className="eyebrow">Output</p>
            <CardTitle className="mt-1">What comes back</CardTitle>
            <CardDescription>
              A reviewable deck, not a published post.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 text-sm">
            <div className="flex gap-3">
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ember-500" />
              <p className="text-ink-500"><span className="font-semibold text-ink-900">5–10 PNG slides</span> at 1080×1350, safe margins, no overflow.</p>
            </div>
            <div className="flex gap-3">
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ember-500" />
              <p className="text-ink-500"><span className="font-semibold text-ink-900">Caption, hashtags, alt text</span> for every slide.</p>
            </div>
            <div className="flex gap-3">
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ember-500" />
              <p className="text-ink-500"><span className="font-semibold text-ink-900">Provenance manifest</span> with adapters, prompts, hashes, and sources.</p>
            </div>
            <div className="rule my-1" />
            <p className="text-xs leading-relaxed text-ink-400">
              No API key? The deterministic FakeLLM adapter runs the whole pipeline and marks the job degraded.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
