import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Download, RotateCcw } from "lucide-react";
import { api } from "@/api/client";
import { StageStepper } from "@/components/StageStepper";
import { StatusChip } from "@/components/StatusChip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { elapsed, relativeTime } from "@/lib/utils";
import type { JobDetail as JobDetailType } from "@/types";

const TERMINAL = ["REVIEW_READY", "APPROVED", "REJECTED", "FAILED", "CANCELLED"];

export default function JobDetail() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logRef = useRef<HTMLDivElement>(null);
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    refetchInterval: (query) => {
      const data = query.state.data as JobDetailType | undefined;
      return data && TERMINAL.includes(data.job.status) ? false : 1500;
    },
  });

  const cancel = useMutation({
    mutationFn: () => api.cancelJob(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["job", jobId] }),
  });

  const retry = useMutation({
    mutationFn: () => api.retryJob(jobId),
    onSuccess: (data) => navigate(`/jobs/${data.job_id}`),
  });

  const data = jobQuery.data;
  const events = data?.events_tail ?? [];

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [events.length]);

  useEffect(() => {
    if (data?.job.status === "REVIEW_READY") {
      navigate(`/review/${jobId}`, { replace: true });
    }
  }, [data?.job.status, jobId, navigate]);

  if (jobQuery.isLoading) {
    return <p className="text-sm text-ink-500">Loading job…</p>;
  }
  if (jobQuery.isError || !data) {
    return (
      <div className="flex flex-col gap-4">
        <Link to="/" className="flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900">
          <ArrowLeft className="h-4 w-4" /> Dashboard
        </Link>
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load this job: {(jobQuery.error as Error)?.message ?? "unknown error"}
        </p>
      </div>
    );
  }

  const { job, stages } = data;
  const workerDown = healthQuery.data && !healthQuery.data.worker.alive;

  return (
    <div className="flex flex-col gap-7">
      <div>
        <Link to="/" className="mb-5 flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900">
          <ArrowLeft className="h-4 w-4" /> Dashboard
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="eyebrow">{job.job_id}</span>
              <StatusChip status={job.status} />
            </div>
            <h1 className="page-title mt-2 max-w-2xl">{job.topic}</h1>
            <p className="mt-2 text-sm text-ink-500">
              {job.plugin} · started {relativeTime(job.started_at)} · {elapsed(job.started_at, job.finished_at)} elapsed
            </p>
          </div>
          <div className="flex gap-2">
            {(job.status === "QUEUED" || job.status === "RUNNING") && (
              <Button variant="outline" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
                {cancel.isPending ? "Cancelling…" : "Cancel"}
              </Button>
            )}
            {job.status === "FAILED" && (
              <Button onClick={() => retry.mutate()} disabled={retry.isPending}>
                <RotateCcw className="h-4 w-4" /> Retry
              </Button>
            )}
            {job.status === "REVIEW_READY" && (
              <Button asChild variant="ember">
                <a href={`/media/review/${job.job_id}/carousel.zip`} download>
                  <Download className="h-4 w-4" /> Download zip
                </a>
              </Button>
            )}
          </div>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <StageStepper stages={stages} />
        </CardContent>
      </Card>

      {job.status === "RUNNING" && (
        <div>
          <div className="h-1.5 overflow-hidden rounded-full bg-ink-900/10">
            <div className="h-full bg-ember-500 transition-all" style={{ width: `${Math.round(job.progress * 100)}%` }} />
          </div>
          <p className="mt-2 text-xs text-ink-400">
            {Math.round(job.progress * 100)}% · {job.stage ?? "starting"}
          </p>
        </div>
      )}

      {job.status === "QUEUED" && workerDown && (
        <p className="rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          This job is queued because no worker is running. Start it with{" "}
          <code className="rounded bg-amber-900/10 px-1.5 py-0.5 font-mono text-xs">make worker</code>.
        </p>
      )}

      {job.status === "FAILED" && job.error && (
        <div className="rounded-card border border-red-200 bg-red-50 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="danger">{job.error.error_class}</Badge>
            {job.error.stage && <span className="text-xs font-semibold uppercase tracking-wide text-red-700/70">at {job.error.stage}</span>}
          </div>
          <p className="mt-3 text-sm leading-relaxed text-red-800">{job.error.message}</p>
          <a
            href={`/api/jobs/${job.job_id}/logs`}
            className="mt-3 inline-block text-xs font-semibold text-red-700 underline underline-offset-2"
          >
            Download logs
          </a>
        </div>
      )}

      {job.status === "REVIEW_READY" && (
        <Card className="border-ember-500/25 bg-ember-500/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
            <div>
              <p className="text-sm font-semibold text-ink-900">Deck is ready for review</p>
              <p className="mt-1 text-sm text-ink-500">
                Artifact at <code className="font-mono text-xs">review/{job.job_id}/</code>. Approve or edit it on the
                review page.
              </p>
            </div>
            <Badge variant="ember">review pending</Badge>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Live log</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              ref={logRef}
              className="max-h-80 overflow-y-auto rounded-xl bg-ink-900 p-4 font-mono text-[11px] leading-relaxed text-cream-200"
            >
              {events.length === 0 ? (
                <p className="text-cream-200/40">Waiting for worker events…</p>
              ) : (
                events.map((event) => (
                  <div key={event.id} className="flex gap-3">
                    <span className="shrink-0 text-cream-200/35">{event.ts.slice(11, 19)}</span>
                    <span className={event.level === "error" ? "text-red-300" : "text-cream-200/80"}>
                      <span className="uppercase text-ember-400/80">{event.stage ?? "job"}</span> {event.message}
                    </span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Job facts</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            {[
              ["Plugin", job.plugin],
              ["Seed", String(job.seed)],
              ["Created", relativeTime(job.created_at)],
              ["Finished", job.finished_at ? relativeTime(job.finished_at) : "—"],
              ["Recommended", job.recommended_plugin ?? "—"],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between gap-4 border-b border-ink-900/5 pb-2 last:border-0">
                <span className="text-ink-400">{label}</span>
                <span className="text-right font-medium text-ink-900">{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
