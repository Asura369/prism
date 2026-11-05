import { Link } from "react-router";
import { STATUS_META } from "@/components/StatusChip";
import { relativeTime } from "@/lib/utils";
import type { JobSummary } from "@/types";

function pluginLabel(name: string) {
  return name.replace("_carousel", "");
}

export function JobCard({ job, showStatus = true }: { job: JobSummary; showStatus?: boolean }) {
  const status = STATUS_META[job.status];
  const running = job.status === "RUNNING";

  return (
    <Link
      to={`/jobs/${job.job_id}`}
      className="group relative flex flex-col border-b border-r border-ink-900/10 bg-paper-50 transition-colors hover:bg-[#f9f8f2] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ink-900"
    >
      <span className={`absolute inset-x-0 top-0 z-10 h-[3px] ${status.band}`} aria-hidden />
      <div className="relative aspect-[4/5] overflow-hidden bg-paper-200">
        {job.thumbnail_url ? (
          <img
            src={job.thumbnail_url}
            alt={`Thumbnail for ${job.topic}`}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.015] motion-reduce:transition-none"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-paper-200/40 p-4">
            <span className="border border-dashed border-ink-900/20 px-2.5 py-1.5 text-[9.5px] font-medium uppercase tracking-[0.1em] text-ink-400">
              no render on disk
            </span>
          </div>
        )}
        {showStatus ? (
          <span className="absolute left-2.5 top-3 rounded-[2px] border border-ink-900/12 bg-paper-50/92 px-1.5 py-[3px]">
            <span className="text-[9.5px] font-semibold uppercase tracking-[0.08em] text-ink-700">
              {job.status === "REVIEW_READY" ? "Awaiting you" : status.label}
            </span>
          </span>
        ) : null}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 px-3 py-3">
        <div className="flex items-baseline justify-between gap-2">
          <span className="fac tnum hidden truncate sm:block">{job.job_id}</span>
          <span className="fac ml-auto shrink-0 text-ink-400/80">{relativeTime(job.created_at)}</span>
        </div>
        <p className="line-clamp-2 text-[13.5px] font-semibold leading-[1.35] text-ink-900">{job.topic}</p>
        <div className="mt-auto flex items-center justify-between gap-2 pt-1">
          <span className="text-[11px] text-ink-400">{pluginLabel(job.plugin)}</span>
          {running ? (
            <span className="tnum text-[11px] text-ink-400">
              {job.stage ?? "starting"} · {Math.round(job.progress * 100)}%
            </span>
          ) : null}
        </div>
        {running ? (
          <div className="h-[2px] w-full overflow-hidden bg-ink-900/10">
            <div className="h-full bg-spectrum-render" style={{ width: `${Math.round(job.progress * 100)}%` }} />
          </div>
        ) : null}
      </div>
    </Link>
  );
}
