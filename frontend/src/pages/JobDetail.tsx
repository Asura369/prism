import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import { Download, RotateCcw } from "lucide-react";
import { api } from "@/api/client";
import { SectionHeading } from "@/components/Plate";
import { StageStepper } from "@/components/StageStepper";
import { StatusChip } from "@/components/StatusChip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { elapsed, relativeTime } from "@/lib/utils";
import type { JobDetail as JobDetailType } from "@/types";

const TERMINAL = ["REVIEW_READY", "APPROVED", "REJECTED", "FAILED", "CANCELLED"];

/** Older rows may carry no started_at; never call a finished job "waiting for the worker". */
function timing(job: JobDetailType["job"]): string {
  if (job.started_at) {
    return `started ${relativeTime(job.started_at)} · ${elapsed(job.started_at, job.finished_at)} elapsed`;
  }
  if (job.status === "QUEUED" || job.status === "RUNNING") {
    return `queued ${relativeTime(job.created_at)} · waiting for the worker`;
  }
  const finished = job.finished_at ? ` · finished ${relativeTime(job.finished_at)}` : "";
  return `created ${relativeTime(job.created_at)}${finished}`;
}

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
    return (
      <div className="flex flex-col gap-4">
        <div className="h-6 w-56 animate-pulse rounded-[2px] bg-paper-200" />
        <div className="h-24 animate-pulse rounded-plate border border-ink-900/10 bg-paper-50" />
      </div>
    );
  }

  if (jobQuery.isError || !data) {
    return (
      <div className="flex flex-col gap-4">
        <Link to="/" className="text-[12px] font-medium text-ink-500 hover:text-ink-900">
          ← Queue
        </Link>
        <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">
          Could not load this job: {(jobQuery.error as Error)?.message ?? "unknown error"}
        </p>
      </div>
    );
  }

  const { job, stages } = data;
  const workerDown = healthQuery.data && !healthQuery.data.worker.alive;

  return (
    <div className="flex flex-col gap-6">
      <header className="border-b border-ink-900/12 pb-5">
        <Link
          to="/"
          className="mb-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-500 transition-colors hover:text-ink-900"
        >
          ← Queue
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
          <div className="min-w-0 basis-full sm:basis-auto">
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-2">
              <span className="fac">{job.job_id}</span>
              <StatusChip status={job.status} />
              <Badge variant="outline">{job.plugin.replace("_carousel", "")}</Badge>
            </div>
            <h1 className="mt-2 max-w-3xl text-[21px] font-semibold leading-[1.14] tracking-[-0.022em] text-ink-900 sm:text-[24px] lg:text-[26px]">
              {job.topic}
            </h1>
            <p className="mt-2 text-[12.5px] text-ink-500">{timing(job)}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {job.status === "QUEUED" || job.status === "RUNNING" ? (
              <Button variant="outline" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
                {cancel.isPending ? "Cancelling…" : "Cancel job"}
              </Button>
            ) : null}
            {job.status === "FAILED" ? (
              <Button onClick={() => retry.mutate()} disabled={retry.isPending}>
                <RotateCcw className="h-3.5 w-3.5" /> Retry
              </Button>
            ) : null}
            {job.status === "REVIEW_READY" ? (
              <Button asChild>
                <a href={`/media/review/${job.job_id}/carousel.zip`} download>
                  <Download className="h-3.5 w-3.5" /> Download zip
                </a>
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <section>
        <SectionHeading aside={`${stages.length} stages`}>Pipeline</SectionHeading>
        <StageStepper stages={stages} />
      </section>

      {job.status === "QUEUED" && workerDown ? (
        <p className="border border-spectrum-policy/35 bg-spectrum-policy/[0.07] px-3.5 py-2.5 text-[12.5px] text-[#7c4a12]">
          This job is queued because no worker is running. Start it with{" "}
          <code className="rounded-[2px] bg-[#7c4a12]/10 px-1 font-mono text-[11px]">make worker</code>.
        </p>
      ) : null}

      {job.status === "FAILED" && job.error ? (
        <div className="border border-signal/30 bg-signal/[0.05] p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="danger">{job.error.error_class}</Badge>
            {job.error.stage ? (
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#a32d1b]/75">
                at {job.error.stage}
              </span>
            ) : null}
          </div>
          <p className="mt-2.5 max-w-[75ch] text-[12.5px] leading-relaxed text-[#7a2b1c]">{job.error.message}</p>
          <a
            href={`/api/jobs/${job.job_id}/logs`}
            className="mt-2.5 inline-block text-[11px] font-semibold text-[#a32d1b] underline decoration-[#a32d1b]/30 underline-offset-2 hover:decoration-[#a32d1b]"
          >
            Download logs
          </a>
        </div>
      ) : null}

      {job.status === "REVIEW_READY" ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border border-ink-900/15 bg-paper-50 px-4 py-3.5">
          <div>
            <p className="text-[13px] font-semibold text-ink-900">Deck is ready for review</p>
            <p className="mt-0.5 text-[11.5px] text-ink-500">
              Artifact at <code className="font-mono text-[11px]">review/{job.job_id}/</code>. Edit metadata and decide on
              the review plate.
            </p>
          </div>
          <Badge variant="default">Awaiting you</Badge>
        </div>
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section>
          <SectionHeading aside="tail 200 events">Live log</SectionHeading>
          <div
            ref={logRef}
            className="max-h-80 overflow-y-auto rounded-plate border border-ink-900/12 bg-gate-900 p-3.5 font-mono text-[10.5px] leading-[1.7]"
          >
            {events.length === 0 ? (
              <p className="text-paper-50/35">Waiting for worker events…</p>
            ) : (
              events.map((event) => (
                <div key={event.id} className="flex gap-3">
                  <span className="tnum shrink-0 text-paper-50/30">{event.ts.slice(11, 19)}</span>
                  <span className={event.level === "error" ? "text-[#ff9a8a]" : "text-paper-200/80"}>
                    <span className="uppercase tracking-[0.08em] text-paper-50/40">{event.stage ?? "job"}</span>{" "}
                    {event.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        <section>
          <SectionHeading>Job facts</SectionHeading>
          <dl className="flex flex-col">
            {[
              ["Plugin", job.plugin],
              ["Seed", String(job.seed)],
              ["Created", relativeTime(job.created_at)],
              ["Finished", job.finished_at ? relativeTime(job.finished_at) : "—"],
              ["Recommended", job.recommended_plugin ?? "—"],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex items-baseline justify-between gap-4 border-b border-ink-900/8 py-1.5 last:border-0"
              >
                <dt className="shrink-0 text-[12px] text-ink-400">{label}</dt>
                <dd className="tnum min-w-0 truncate text-right text-[12.5px] font-medium text-ink-900">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  );
}
