import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { api } from "@/api/client";
import { AngleCard } from "@/components/AngleCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { TrendCandidate } from "@/types";

export default function Angles() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const candidateId = params.get("candidate_id") ?? "";
  const [pluginChoices, setPluginChoices] = useState<Record<number, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);

  const candidate = useMemo<TrendCandidate | null>(() => {
    const state = location.state as { candidate?: TrendCandidate } | null;
    if (state?.candidate) return state.candidate;
    try {
      const raw = sessionStorage.getItem(`prism:candidate:${candidateId}`);
      return raw ? (JSON.parse(raw) as TrendCandidate) : null;
    } catch {
      return null;
    }
  }, [candidateId, location.state]);

  const anglesQuery = useQuery({
    queryKey: ["angles", candidateId],
    queryFn: () => api.angles(candidateId),
    enabled: Boolean(candidateId),
    retry: false,
  });
  const pluginsQuery = useQuery({ queryKey: ["plugins"], queryFn: api.plugins });
  const plugins = pluginsQuery.data ?? [];

  const select = useMutation({
    mutationFn: ({ index, plugin }: { index: number; plugin: string }) =>
      api.selectAngle(candidateId, index, plugin),
    onSuccess: (data) => {
      const draft = data.draft_job_payload;
      const next = new URLSearchParams({
        plugin: draft.plugin,
        topic: draft.topic,
        angle: JSON.stringify(draft.angle),
      });
      navigate(`/new?${next.toString()}`);
    },
    onError: (err: Error) => setActionError(err.message),
  });

  const angles = anglesQuery.data?.angles ?? [];
  const candidateInfo = candidate ?? anglesQuery.data?.candidate?.candidate ?? null;

  function effectivePlugin(index: number, recommended: string): string {
    return pluginChoices[index] ?? recommended;
  }

  if (!candidateId) {
    return <p className="text-sm text-ink-500">No candidate selected. Start from Discover.</p>;
  }

  return (
    <div className="flex flex-col gap-7">
      <div>
        <Link to="/discover" className="mb-5 flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900">
          <ArrowLeft className="h-4 w-4" /> Discover
        </Link>
        <p className="eyebrow">Angles</p>
        <h1 className="page-title mt-2 max-w-3xl">{candidateInfo?.title ?? "Selected topic"}</h1>
        <p className="mt-2 text-sm text-ink-500">
          Three ways in. The recommendation is a starting point; override the plugin if another format fits better.
        </p>
      </div>

      {anglesQuery.isError && (
        <Card className="border-amber-300/60 bg-amber-50">
          <CardContent className="flex flex-col items-start gap-3 py-6">
            <p className="text-sm text-amber-900">
              {(anglesQuery.error as Error).message || "Could not load angles."}
            </p>
            <Button asChild variant="outline" size="sm">
              <Link to="/discover">Back to Discover</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {actionError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{actionError}</p>
      )}

      {anglesQuery.isLoading && (
        <div className="grid gap-5 lg:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div key={item} className="h-80 animate-pulse rounded-card border border-ink-900/10 bg-white/50" />
          ))}
        </div>
      )}

      {angles.length > 0 && (
        <>
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => anglesQuery.refetch()} disabled={anglesQuery.isFetching}>
              <RefreshCw className={`h-3.5 w-3.5 ${anglesQuery.isFetching ? "animate-spin" : ""}`} />
              Regenerate angles
            </Button>
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            {angles.map((angle, index) => (
              <AngleCard
                key={`${angle.hook}-${index}`}
                angle={angle}
                index={index}
                plugins={plugins}
                selectedPlugin={effectivePlugin(index, angle.recommended_plugin)}
                onPluginChange={(plugin) => setPluginChoices((current) => ({ ...current, [index]: plugin }))}
                onUse={() => select.mutate({ index, plugin: effectivePlugin(index, angle.recommended_plugin) })}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
