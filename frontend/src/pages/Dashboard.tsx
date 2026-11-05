import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { Compass, Plus } from "lucide-react";
import { api } from "@/api/client";
import { DispersionBar, type DispersionSegment } from "@/components/Dispersion";
import { JobCard } from "@/components/JobCard";
import { PlateHeader } from "@/components/Plate";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { JobSummary } from "@/types";

type TabKey = "review" | "all" | "failed";

function filterJobs(jobs: JobSummary[], tab: TabKey): JobSummary[] {
  if (tab === "review") return jobs.filter((j) => j.status === "REVIEW_READY");
  if (tab === "failed") return jobs.filter((j) => j.status === "FAILED");
  return jobs;
}

function EmptyState({ tab }: { tab: TabKey }) {
  const copy =
    tab === "review"
      ? "Nothing is waiting on you. Start a job and the worker will fill this queue."
      : tab === "failed"
        ? "No failed jobs. Every stage finished clean."
        : "No jobs yet. Pick a topic and the pipeline does the rest.";
  return (
    <div className="flex flex-col items-start justify-center rounded-plate border border-dashed border-ink-900/20 bg-paper-50/50 px-8 py-16">
      <p className="max-w-sm text-[13px] leading-relaxed text-ink-500">{copy}</p>
      <Button asChild variant="outline" size="sm" className="mt-5">
        <Link to="/new">
          <Plus className="h-3.5 w-3.5" /> Create a job
        </Link>
      </Button>
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState<TabKey>("review");
  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.listJobs(),
    refetchInterval: 1500,
  });
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });

  const jobs = useMemo(() => jobsQuery.data?.items ?? [], [jobsQuery.data]);
  const visible = filterJobs(jobs, tab);

  const queued = jobs.filter((j) => j.status === "QUEUED").length;
  const running = jobs.filter((j) => j.status === "RUNNING").length;
  const pendingReview = jobs.filter((j) => j.status === "REVIEW_READY").length;
  const approved = jobs.filter((j) => j.status === "APPROVED").length;
  const failed = jobs.filter((j) => j.status === "FAILED").length;

  const segments: DispersionSegment[] = [
    { key: "review", label: "awaiting review", count: pendingReview, fill: "bg-ink-900" },
    { key: "queued", label: "queued", count: queued, fill: "bg-spectrum-spec" },
    { key: "running", label: "running", count: running, fill: "bg-spectrum-render" },
    { key: "approved", label: "approved", count: approved, fill: "bg-spectrum-export" },
    { key: "failed", label: "failed", count: failed, fill: "bg-signal" },
  ];

  const TABS: [TabKey, string, number][] = [
    ["review", "Awaiting review", pendingReview],
    ["all", "All", jobs.length],
    ["failed", "Failed", failed],
  ];

  const workerDown = healthQuery.data && !healthQuery.data.worker.alive;

  return (
    <div className="flex flex-col gap-6">
      <PlateHeader
        title="Review queue"
        meta={
          jobsQuery.isLoading ? (
            "Reading the queue…"
          ) : (
            <>
              <span className="tnum font-semibold text-ink-900">{pendingReview}</span> waiting on you
              <span className="mx-2 text-ink-300" aria-hidden>
                /
              </span>
              worker {healthQuery.data?.worker.alive ? "live" : "offline"}
            </>
          )
        }
        actions={
          <>
            <Button asChild variant="outline">
              <Link to="/discover">
                <Compass className="h-3.5 w-3.5" /> Discover
              </Link>
            </Button>
            <Button asChild>
              <Link to="/new">
                <Plus className="h-3.5 w-3.5" /> New job
              </Link>
            </Button>
          </>
        }
      />

      {jobs.length > 0 ? (
        <div className="border-b border-ink-900/12 pb-5">
          <DispersionBar segments={segments} />
        </div>
      ) : null}

      {workerDown && queued > 0 ? (
        <p className="border border-spectrum-policy/35 bg-spectrum-policy/[0.07] px-3.5 py-2.5 text-[12.5px] text-[#7c4a12]">
          {queued} job{queued === 1 ? "" : "s"} waiting for a worker. Nothing will move until{" "}
          <code className="rounded-[2px] bg-[#7c4a12]/10 px-1 font-mono text-[11px]">make worker</code> runs.
        </p>
      ) : null}

      {jobsQuery.isError ? (
        <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">
          Could not load jobs: {(jobsQuery.error as Error).message}
        </p>
      ) : null}

      <section className="flex flex-col">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div role="tablist" aria-label="Queue filters" className="flex items-center border-b border-ink-900/12">
            {TABS.map(([key, label, count]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={tab === key}
                aria-controls="queue-panel"
                id={`queue-tab-${key}`}
                onClick={() => setTab(key)}
                className={cn(
                  "relative -mb-px h-9 px-3 text-[12.5px] font-medium transition-colors first:pl-0",
                  tab === key ? "text-ink-900" : "text-ink-400 hover:text-ink-700",
                )}
              >
                {label}
                <span className="tnum ml-1.5 text-[11px] text-ink-400">{count}</span>
                {tab === key ? <span className="absolute inset-x-0 -bottom-px h-[2px] bg-ink-900" aria-hidden /> : null}
              </button>
            ))}
          </div>
          <span className="tnum pb-1.5 text-[11px] text-ink-400">
            {jobsQuery.isLoading ? "Loading…" : `${visible.length} shown`}
          </span>
        </div>

        <div className="mt-5" role="tabpanel" id="queue-panel" aria-labelledby={`queue-tab-${tab}`}>
          {!jobsQuery.isLoading && visible.length === 0 ? (
            <EmptyState tab={tab} />
          ) : visible.length === 0 ? (
            <div className="grid grid-cols-2 border-l border-t border-ink-900/10 sm:grid-cols-3 xl:grid-cols-4">
              {[0, 1, 2, 3].map((item) => (
                <div key={item} className="flex flex-col border-b border-r border-ink-900/10 bg-paper-50">
                  <div className="aspect-[4/5] animate-pulse bg-paper-200/70" />
                  <div className="space-y-2 px-3 py-3">
                    <div className="h-2 w-16 animate-pulse rounded-full bg-paper-200" />
                    <div className="h-2.5 w-full animate-pulse rounded-full bg-paper-200" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 border-l border-t border-ink-900/10 sm:grid-cols-3 xl:grid-cols-4">
              {visible.map((job) => (
                <JobCard key={job.job_id} job={job} showStatus={tab !== "review"} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
