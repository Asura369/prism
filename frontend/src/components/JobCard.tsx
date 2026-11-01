import { Link } from "react-router-dom";
import { StatusChip } from "@/components/StatusChip";
import { Badge } from "@/components/ui/badge";
import { relativeTime } from "@/lib/utils";
import type { JobSummary } from "@/types";

export function JobCard({ job }: { job: JobSummary }) {
  return (
    <Link
      to={`/jobs/${job.job_id}`}
      className="group flex flex-col overflow-hidden rounded-card border border-ink-900/10 bg-white/70 shadow-card transition-transform hover:-translate-y-0.5"
    >
      <div className="relative aspect-[4/5] overflow-hidden bg-cream-100">
        {job.thumbnail_url ? (
          <img
            src={job.thumbnail_url}
            alt={`Thumbnail for ${job.topic}`}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.02]"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-cream-100 to-cream-200">
            <span className="text-5xl font-bold text-ink-900/10">P</span>
          </div>
        )}
        <div className="absolute left-3 top-3">
          <StatusChip status={job.status} />
        </div>
      </div>
      <div className="flex flex-col gap-2 p-4">
        <div className="flex items-center justify-between gap-2">
          <Badge variant="outline">{job.plugin.replace("_carousel", "")}</Badge>
          <span className="text-[11px] text-ink-400">{relativeTime(job.created_at)}</span>
        </div>
        <p className="line-clamp-2 text-sm font-semibold leading-snug text-ink-900">{job.topic}</p>
        {job.stage && job.status === "RUNNING" && (
          <div className="mt-1">
            <div className="h-1 overflow-hidden rounded-full bg-ink-900/10">
              <div className="h-full bg-ember-500" style={{ width: `${Math.round(job.progress * 100)}%` }} />
            </div>
            <p className="mt-1 text-[11px] capitalize text-ink-400">{job.stage} · {Math.round(job.progress * 100)}%</p>
          </div>
        )}
      </div>
    </Link>
  );
}
