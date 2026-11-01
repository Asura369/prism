import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Compass, Plus } from "lucide-react";
import { api } from "@/api/client";
import { JobCard } from "@/components/JobCard";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
      ? "No decks waiting for review. Create a job and the worker will fill this queue."
      : tab === "failed"
        ? "No failed jobs. Nice."
        : "No jobs yet. Start with a topic.";
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-ink-900/15 bg-white/40 px-8 py-20 text-center">
      <p className="max-w-sm text-sm leading-relaxed text-ink-500">{copy}</p>
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
  const workerDown = healthQuery.data && !healthQuery.data.worker.alive;

  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1 className="page-title mt-2">Carousel pipeline</h1>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-ink-500">
            Every deck lands here for review. Approve what reads well, reject what doesn&apos;t.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/discover">
              <Compass className="h-4 w-4" /> Discover trends
            </Link>
          </Button>
          <Button asChild>
            <Link to="/new">
              <Plus className="h-4 w-4" /> New job
            </Link>
          </Button>
        </div>
      </div>

      {workerDown && queued > 0 && (
        <p className="rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {queued} job{queued === 1 ? "" : "s"} waiting for a worker.
        </p>
      )}

      <Tabs value={tab} onValueChange={(value) => setTab(value as TabKey)}>
        <div className="flex items-center justify-between gap-4">
          <TabsList>
            <TabsTrigger value="review">
              Review queue{jobs.filter((j) => j.status === "REVIEW_READY").length ? ` · ${jobs.filter((j) => j.status === "REVIEW_READY").length}` : ""}
            </TabsTrigger>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="failed">Failed</TabsTrigger>
          </TabsList>
          <span className="text-xs text-ink-400">{jobsQuery.isLoading ? "Loading…" : `${visible.length} deck${visible.length === 1 ? "" : "s"}`}</span>
        </div>

        <TabsContent value={tab}>
          {jobsQuery.isError && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              Could not load jobs: {(jobsQuery.error as Error).message}
            </p>
          )}
          {!jobsQuery.isLoading && visible.length === 0 ? (
            <EmptyState tab={tab} />
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {visible.map((job) => (
                <JobCard key={job.job_id} job={job} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
