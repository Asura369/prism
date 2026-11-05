import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { RefreshCw } from "lucide-react";
import { api } from "@/api/client";
import { AngleCard } from "@/components/AngleCard";
import { PlateHeader } from "@/components/Plate";
import { Button } from "@/components/ui/button";
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
    return <p className="text-[13px] text-ink-500">No candidate selected. Start from Discover.</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <PlateHeader
        title={candidateInfo?.title ?? "Selected topic"}
        back={
          <Link to="/discover" className="mb-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-500 transition-colors hover:text-ink-900">
            ← Discover
          </Link>
        }
        meta="Three ways in. The route is a starting point; override the plugin if another format fits better."
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => anglesQuery.refetch()}
            disabled={anglesQuery.isFetching}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${anglesQuery.isFetching ? "animate-spin" : ""}`} /> Regenerate angles
          </Button>
        }
      />

      {anglesQuery.isError ? (
        <div className="border border-spectrum-policy/35 bg-spectrum-policy/[0.07] px-3.5 py-3">
          <p className="text-[12.5px] text-[#7c4a12]">
            {(anglesQuery.error as Error).message || "Could not load angles."}
          </p>
          <Button asChild variant="outline" size="sm" className="mt-2.5">
            <Link to="/discover">Back to Discover</Link>
          </Button>
        </div>
      ) : null}

      {actionError ? (
        <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">
          {actionError}
        </p>
      ) : null}

      {anglesQuery.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div key={item} className="h-72 animate-pulse rounded-plate border border-ink-900/10 bg-paper-50" />
          ))}
        </div>
      ) : angles.length === 0 ? (
        <div className="rounded-plate border border-dashed border-ink-900/20 bg-paper-50/50 px-6 py-12">
          <p className="max-w-md text-[12.5px] leading-relaxed text-ink-500">
            This run produced no angles. Regenerate them, or pick a different candidate from Discover.
          </p>
          <Button asChild variant="outline" size="sm" className="mt-4">
            <Link to="/discover">Back to Discover</Link>
          </Button>
        </div>
      ) : angles.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-3">
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
      ) : null}
    </div>
  );
}
