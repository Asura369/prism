import { Link } from "react-router";
import { ArrowUpRight } from "lucide-react";
import type { ScoredCandidate } from "@/types";

const SOURCE_LABELS: Record<string, string> = {
  google_news_rss: "Google News",
  hackernews: "Hacker News",
  google_trends_csv: "Trends CSV",
  manual: "Manual",
};

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="text-ink-400">{label}</span>
      <span className="relative block h-[4px] w-14 overflow-hidden rounded-[1px] bg-ink-900/10" aria-hidden>
        <span className="absolute inset-y-0 left-0 rounded-[1px] bg-ink-900/55" style={{ width: `${Math.round(value * 100)}%` }} />
      </span>
      <span className="tnum text-ink-500">{value.toFixed(2)}</span>
    </span>
  );
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
      className="group grid grid-cols-[1.6rem_1fr_auto] items-start gap-3 border-b border-ink-900/10 py-4 pr-1 transition-colors hover:bg-ink-900/[0.025] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900"
    >
      <span className="fac tnum pt-1 text-[10.5px] text-ink-400">{String(rank).padStart(2, "0")}</span>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
          <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-500">
            {SOURCE_LABELS[candidate.source] ?? candidate.source}
          </span>
          {clusterSize > 1 ? (
            <span className="fac text-ink-400">{`${clusterSize} sources`}</span>
          ) : null}
        </div>

        <h3 className="mt-1 text-[15px] font-semibold leading-snug tracking-[-0.01em] text-ink-900">
          {candidate.title}
        </h3>
        {candidate.snippet ? (
          <p className="mt-1 line-clamp-2 max-w-[68ch] text-[12.5px] leading-relaxed text-ink-500">
            {candidate.snippet}
          </p>
        ) : null}

        <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10.5px]">
          <Metric label="safety" value={score.safety} />
          <Metric label="angles" value={score.angle_ability} />
          <Metric label="visual" value={score.visual_potential} />
        </div>

        {score.reasoning ? (
          <p className="mt-2 max-w-[68ch] text-[11.5px] leading-relaxed text-ink-400">{score.reasoning}</p>
        ) : null}
      </div>

      <div className="flex h-full flex-col items-end justify-between gap-2 pl-2">
        <div className="text-right">
          <span className="tnum block text-[20px] font-semibold leading-none tracking-[-0.02em] text-ink-900">
            {Math.round(score.combined * 100)}
          </span>
          <span className="fac mt-1 block text-[9px]">score</span>
        </div>
        <span className="flex items-center gap-1 text-[11px] font-medium text-ink-400 transition-colors group-hover:text-ink-900">
          3 angles
          <ArrowUpRight className="h-3 w-3 transition-transform group-hover:-translate-y-px group-hover:translate-x-px motion-reduce:transition-none" />
        </span>
      </div>
    </Link>
  );
}
