import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Upload } from "lucide-react";
import { api } from "@/api/client";
import { CandidateCard } from "@/components/CandidateCard";
import { SourceToggleGroup, type SourceOption } from "@/components/SourceToggleGroup";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { DiscoverResponse, ScoredCandidate } from "@/types";

const FETCHABLE: SourceOption[] = [
  { name: "google_news_rss", label: "Google News" },
  { name: "hackernews", label: "Hacker News" },
];
const REGIONS = ["US", "GB", "CA", "AU", "IN"];
const WINDOWS = [
  [24, "24 hours"],
  [48, "48 hours"],
  [168, "7 days"],
] as const;

function dedupe(candidates: ScoredCandidate[]): ScoredCandidate[] {
  const seen = new Set<string>();
  return candidates.filter((item) => {
    if (seen.has(item.candidate.id)) return false;
    seen.add(item.candidate.id);
    return true;
  });
}

export default function Discover() {
  const queryClient = useQueryClient();
  const [region, setRegion] = useState("US");
  const [windowH, setWindowH] = useState<number>(24);
  const [selected, setSelected] = useState<string[] | null>(null);
  const [title, setTitle] = useState("");
  const [snippet, setSnippet] = useState("");
  const [url, setUrl] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.settings });

  const sourceSettings = useMemo(() => {
    const discovery = settingsQuery.data?.config.discovery as
      | { sources?: Record<string, { enabled?: boolean }> }
      | undefined;
    return discovery?.sources ?? {};
  }, [settingsQuery.data]);

  const availableSources = useMemo(
    () => FETCHABLE.filter((source) => sourceSettings[source.name]?.enabled !== false),
    [sourceSettings],
  );

  useEffect(() => {
    if (selected === null && settingsQuery.data) {
      setSelected(availableSources.map((source) => source.name));
    }
  }, [availableSources, selected, settingsQuery.data]);

  const activeSources = selected ?? [];
  const queryKey = ["trends", region, windowH, activeSources] as const;
  const trendsQuery = useQuery({
    queryKey,
    queryFn: () => api.trends({ region, windowH, sources: activeSources }),
    enabled: selected !== null && activeSources.length > 0,
    staleTime: 60_000,
  });

  const candidates = trendsQuery.data?.candidates ?? [];

  function mergeCandidates(items: ScoredCandidate[]) {
    queryClient.setQueryData<DiscoverResponse>(queryKey, (previous) => {
      const base: DiscoverResponse =
        previous ?? {
          fetched_at: new Date().toISOString(),
          sources_used: [],
          sources_failed: [],
          candidates: [],
        };
      return { ...base, candidates: dedupe([...base.candidates, ...items]) };
    });
  }

  const manual = useMutation({
    mutationFn: () => api.manualIdea({ title: title.trim(), snippet: snippet.trim(), url: url.trim() }),
    onSuccess: (data) => {
      mergeCandidates([data.candidate]);
      setTitle("");
      setSnippet("");
      setUrl("");
      setNotice("Manual candidate added.");
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadTrends(file),
    onSuccess: (data) => {
      mergeCandidates(data.candidates);
      setNotice(`Imported ${data.imported_count} row${data.imported_count === 1 ? "" : "s"} from CSV.`);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const isLoading = trendsQuery.isLoading;
  const allFailed =
    !isLoading && candidates.length === 0 && (trendsQuery.data?.sources_failed.length ?? 0) > 0;

  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Discover</p>
          <h1 className="page-title mt-2">Find the next topic</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-500">
            Pull candidates from enabled sources, score them for safety and carousel viability, then pick an angle.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-5 pt-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                Region
                <select
                  value={region}
                  onChange={(event) => setRegion(event.target.value)}
                  className="h-10 rounded-xl border border-ink-900/15 bg-white px-3 text-sm font-normal text-ink-900"
                >
                  {REGIONS.map((code) => (
                    <option key={code} value={code}>
                      {code}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                Window
                <select
                  value={windowH}
                  onChange={(event) => setWindowH(Number(event.target.value))}
                  className="h-10 rounded-xl border border-ink-900/15 bg-white px-3 text-sm font-normal text-ink-900"
                >
                  {WINDOWS.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-ink-900/15 bg-white/60 px-4 py-2 text-xs font-semibold text-ink-700 hover:border-ink-900/30">
                <Upload className="h-3.5 w-3.5" />
                {upload.isPending ? "Importing…" : "Upload Trends CSV"}
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  disabled={upload.isPending}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) upload.mutate(file);
                    event.target.value = "";
                  }}
                />
              </label>
              <Button variant="outline" size="sm" onClick={() => trendsQuery.refetch()} disabled={!activeSources.length}>
                Refresh
              </Button>
            </div>
          </div>

          <div>
            <p className="eyebrow mb-2">Sources</p>
            {settingsQuery.isLoading ? (
              <p className="text-xs text-ink-400">Loading sources…</p>
            ) : availableSources.length === 0 ? (
              <p className="text-xs text-ink-400">No fetchable sources are enabled in config.yaml.</p>
            ) : (
              <SourceToggleGroup sources={availableSources} selected={activeSources} onChange={setSelected} />
            )}
            <p className="mt-2 text-[11px] text-ink-400">Reddit is deferred; CSV upload and manual ideas stay available.</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Add a manual idea</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-3 md:grid-cols-[1.2fr_1.5fr_auto]"
            onSubmit={(event) => {
              event.preventDefault();
              if (title.trim()) manual.mutate();
            }}
          >
            <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Topic title" maxLength={200} />
            <Textarea
              value={snippet}
              onChange={(event) => setSnippet(event.target.value)}
              placeholder="Optional context or source URL"
              className="min-h-11 md:min-h-11"
              rows={1}
            />
            <div className="flex gap-2">
              <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="URL (optional)" />
              <Button type="submit" disabled={!title.trim() || manual.isPending}>
                {manual.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Add
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {notice && <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</p>}
      {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {trendsQuery.isError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not fetch candidates: {(trendsQuery.error as Error).message}
        </p>
      )}
      {trendsQuery.data && trendsQuery.data.sources_failed.length > 0 && candidates.length > 0 && (
        <p className="text-xs text-ink-400">
          Some sources failed: {trendsQuery.data.sources_failed.join(", ")}.
        </p>
      )}
      {allFailed && (
        <p className="rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          All selected sources failed. Check your network or start from a manual idea.
        </p>
      )}

      {isLoading ? (
        <div className="grid gap-5 md:grid-cols-2">
          {[0, 1, 2, 3].map((item) => (
            <div key={item} className="h-64 animate-pulse rounded-card border border-ink-900/10 bg-white/50" />
          ))}
        </div>
      ) : candidates.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center text-sm text-ink-500">
            {activeSources.length === 0
              ? "Choose at least one source, upload a CSV, or add a manual idea."
              : "No candidates passed the safety filter. Try another source or add a manual idea."}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {candidates.map((item, index) => (
            <CandidateCard key={item.candidate.id} item={item} rank={index + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
