import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Upload } from "lucide-react";
import { api } from "@/api/client";
import { CandidateCard } from "@/components/CandidateCard";
import { PlateHeader, SectionHeading } from "@/components/Plate";
import { SourceToggleGroup, type SourceOption } from "@/components/SourceToggleGroup";
import { Button } from "@/components/ui/button";
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
    <div className="flex flex-col gap-6">
      <PlateHeader
        title="Find a topic"
        meta="Pull candidates from enabled sources, score them for safety and carousel viability, then pick an angle."
        actions={
          <>
            <label className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-[3px] border border-ink-900/20 px-3 text-[12.5px] font-medium text-ink-900 transition-colors hover:border-ink-900/45 hover:bg-ink-900/[0.04]">
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
            <Button variant="outline" onClick={() => trendsQuery.refetch()} disabled={!activeSources.length}>
              Refresh
            </Button>
          </>
        }
      />

      <section className="rounded-plate border border-ink-900/12 bg-paper-50">
        <div className="grid gap-4 border-b border-ink-900/10 p-4 sm:grid-cols-[120px_140px_minmax(0,1fr)] sm:items-start">
          <label className="flex flex-col gap-1.5">
            <span className="label">Region</span>
            <select
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              className="h-9 rounded-field border border-ink-900/18 bg-paper-50 px-3 text-[13px] text-ink-900 transition-colors hover:border-ink-900/30 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60"
            >
              {REGIONS.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="label">Window</span>
            <select
              value={windowH}
              onChange={(event) => setWindowH(Number(event.target.value))}
              className="h-9 rounded-field border border-ink-900/18 bg-paper-50 px-3 text-[13px] text-ink-900 transition-colors hover:border-ink-900/30 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60"
            >
              {WINDOWS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-col gap-1.5">
            <span className="label">Sources</span>
            {settingsQuery.isLoading ? (
              <p className="text-[11.5px] text-ink-400">Loading sources…</p>
            ) : availableSources.length === 0 ? (
              <p className="text-[11.5px] text-ink-400">No fetchable sources are enabled in config.yaml.</p>
            ) : (
              <SourceToggleGroup sources={availableSources} selected={activeSources} onChange={setSelected} />
            )}
          </div>
        </div>

        <form
          className="grid gap-2 p-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1.3fr)_minmax(0,0.9fr)_auto]"
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
            className="min-h-9 md:min-h-9"
            rows={1}
          />
          <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="URL (optional)" />
          <Button type="submit" disabled={!title.trim() || manual.isPending}>
            {manual.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            Add
          </Button>
        </form>
      </section>

      {notice ? (
        <p className="border border-spectrum-export/35 bg-spectrum-export/[0.07] px-3.5 py-2.5 text-[12.5px] text-[#1f7444]">
          {notice}
        </p>
      ) : null}
      {error ? (
        <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">{error}</p>
      ) : null}
      {trendsQuery.isError ? (
        <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">
          Could not fetch candidates: {(trendsQuery.error as Error).message}
        </p>
      ) : null}
      {trendsQuery.data && trendsQuery.data.sources_failed.length > 0 && candidates.length > 0 ? (
        <p className="text-[11.5px] text-ink-400">
          Some sources failed: {trendsQuery.data.sources_failed.join(", ")}.
        </p>
      ) : null}
      {allFailed ? (
        <p className="border border-spectrum-policy/35 bg-spectrum-policy/[0.07] px-3.5 py-2.5 text-[12.5px] text-[#7c4a12]">
          Every selected source failed. Check the network, or start from a manual idea above.
        </p>
      ) : null}

      <section>
        <SectionHeading aside={isLoading ? "fetching" : `${candidates.length} scored`}>
          Candidates
        </SectionHeading>

        {isLoading ? (
          <div className="rounded-plate border border-ink-900/12 bg-paper-50 px-4">
            {[0, 1, 2, 3].map((item) => (
              <div key={item} className="flex items-start gap-3 border-b border-ink-900/10 py-4 last:border-0">
                <div className="mt-1 h-2.5 w-5 animate-pulse rounded-[1px] bg-paper-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-2 w-24 animate-pulse rounded-[1px] bg-paper-200" />
                  <div className="h-3 w-2/3 animate-pulse rounded-[1px] bg-paper-200" />
                  <div className="h-2.5 w-1/2 animate-pulse rounded-[1px] bg-paper-200" />
                </div>
              </div>
            ))}
          </div>
        ) : candidates.length === 0 ? (
          <div className="rounded-plate border border-dashed border-ink-900/20 bg-paper-50/50 px-6 py-12">
            <p className="max-w-md text-[12.5px] leading-relaxed text-ink-500">
              {activeSources.length === 0
                ? "Choose at least one source, upload a CSV, or add a manual idea."
                : "No candidates passed the safety filter. Try another source or add a manual idea."}
            </p>
          </div>
        ) : (
          <div className="rounded-plate border border-ink-900/12 bg-paper-50 px-4">
            {candidates.map((item, index) => (
              <CandidateCard key={item.candidate.id} item={item} rank={index + 1} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
