import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ScoredCandidate } from "@/types";

const SOURCE_LABELS: Record<string, string> = {
  google_news_rss: "Google News",
  hackernews: "Hacker News",
  google_trends_csv: "Trends CSV",
  manual: "Manual",
  reddit: "Reddit",
};

function scoreVariant(score: number) {
  if (score >= 0.7) return "ember" as const;
  if (score >= 0.5) return "amber" as const;
  return "outline" as const;
}

export function CandidateCard({ item, rank }: { item: ScoredCandidate; rank: number }) {
  const { candidate, score } = item;
  const clusterSize = Number(candidate.metrics.cluster_size ?? 1);

  function remember() {
    try {
      sessionStorage.setItem(`prism:candidate:${candidate.id}`, JSON.stringify(candidate));
    } catch {
      /* session storage unavailable */
    }
  }

  return (
    <Link
      to={`/discover/angles?candidate_id=${encodeURIComponent(candidate.id)}`}
      state={{ candidate }}
      onClick={remember}
      className="group flex flex-col gap-4 rounded-card border border-ink-900/10 bg-white/70 p-5 shadow-card transition-colors hover:border-ink-900/25"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] text-ink-400">{String(rank).padStart(2, "0")}</span>
          <Badge variant="outline">{SOURCE_LABELS[candidate.source] ?? candidate.source}</Badge>
          {clusterSize > 1 && <Badge variant="outline">{clusterSize} sources</Badge>}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge variant={scoreVariant(score.combined)}>{Math.round(score.combined * 100)}</Badge>
          <span className="text-[10px] text-ink-400">score</span>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-bold leading-snug text-ink-900">{candidate.title}</h3>
        {candidate.snippet && (
          <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-500">{candidate.snippet}</p>
        )}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-ink-400">
        <span>safety {score.safety.toFixed(2)}</span>
        <span>angles {score.angle_ability.toFixed(2)}</span>
        <span>visual {score.visual_potential.toFixed(2)}</span>
      </div>

      {score.reasoning && (
        <p className="rounded-lg bg-cream-100 px-3 py-2 text-xs leading-relaxed text-ink-500">{score.reasoning}</p>
      )}

      <span className="mt-auto inline-flex items-center gap-1 text-xs font-semibold text-ember-600">
        See 3 angles <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
