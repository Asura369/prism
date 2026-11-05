import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import { Check, Download, RotateCcw, X } from "lucide-react";
import { api } from "@/api/client";
import { ImageGallery } from "@/components/ImageGallery";
import { MetadataForm } from "@/components/MetadataForm";
import { Facts, PlateHeader, SectionHeading } from "@/components/Plate";
import { ProvenancePanel } from "@/components/ProvenancePanel";
import { SlidePreview } from "@/components/SlidePreview";
import { StatusChip } from "@/components/StatusChip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { safeExternalUrl } from "@/lib/utils";
import type { ReviewMetadata } from "@/types";

interface SourceLink {
  name?: string;
  url?: string;
  title?: string;
}

export default function Review() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [metadataDirty, setMetadataDirty] = useState(false);

  const reviewQuery = useQuery({
    queryKey: ["review", jobId],
    queryFn: () => api.getReview(jobId),
    refetchInterval: 1500,
  });

  const approve = useMutation({
    mutationFn: () => api.approve(jobId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      navigate("/");
    },
    onError: (err: Error) => setActionError(err.message),
  });

  const reject = useMutation({
    mutationFn: () => api.reject(jobId, reason.trim()),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      navigate("/");
    },
    onError: (err: Error) => setActionError(err.message),
  });

  const regenerate = useMutation({
    mutationFn: () => api.retryJob(jobId),
    onSuccess: (data) => navigate(`/jobs/${data.job_id}`),
    onError: (err: Error) => setActionError(err.message),
  });

  if (reviewQuery.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="h-6 w-48 animate-pulse rounded-[2px] bg-paper-200" />
        <div className="h-52 animate-pulse rounded-plate border border-ink-900/10 bg-paper-50" />
      </div>
    );
  }

  if (reviewQuery.isError || !reviewQuery.data) {
    return (
      <div className="flex flex-col gap-4">
        <PlateHeader
          title="Deck unavailable"
          back={
            <Link to="/" className="text-[12px] font-medium text-ink-500 hover:text-ink-900">
              ← Queue
            </Link>
          }
        />
        <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">
          Could not load review: {(reviewQuery.error as Error)?.message ?? "not found"}
        </p>
      </div>
    );
  }

  const { job, metadata, manifest, technical, artifact_urls } = reviewQuery.data;
  const slideCount = artifact_urls.slides.length;
  const rawSources = (manifest.sources ?? (manifest.ingest as Record<string, unknown> | undefined)?.sources) as
    | SourceLink[]
    | undefined;
  const sources = Array.isArray(rawSources) ? rawSources.filter((source) => source?.name || source?.url) : [];

  async function saveMetadata(patch: Partial<ReviewMetadata>): Promise<ReviewMetadata> {
    const response = await api.patchMetadata(jobId, patch);
    queryClient.setQueryData(["review", jobId], (existing: typeof reviewQuery.data) =>
      existing ? { ...existing, metadata: response.metadata } : existing,
    );
    return response.metadata;
  }

  const busy = approve.isPending || reject.isPending;

  return (
    <div className="flex flex-col gap-6">
      <PlateHeader
        title={metadata.title || job.topic}
        back={
          <Link to="/" className="mb-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-500 transition-colors hover:text-ink-900">
            ← Queue
          </Link>
        }
        meta={
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-2">
            <span className="fac">{job.job_id}</span>
            <StatusChip status={job.status} />
            <Badge variant="outline">{job.plugin.replace("_carousel", "")}</Badge>
            <span className="tnum text-ink-400">
              {technical.slide_count} slides · {technical.resolution} · {(technical.total_size_bytes / 1024 / 1024).toFixed(2)} MB
            </span>
          </div>
        }
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <a href={artifact_urls.download} download>
                <Download className="h-3.5 w-3.5" /> Download
              </a>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => regenerate.mutate()}
              disabled={regenerate.isPending}
            >
              <RotateCcw className="h-3.5 w-3.5" /> {regenerate.isPending ? "Requeuing…" : "Regenerate"}
            </Button>
          </>
        }
      />

      {actionError ? (
        <p className="border border-signal/30 bg-signal/[0.06] px-3.5 py-2.5 text-[12.5px] text-[#a32d1b]">
          {actionError}
        </p>
      ) : null}

      {rejectOpen ? (
        <section className="border border-signal/30 bg-[#f7ece7] p-4">
          <label htmlFor="reject-reason" className="text-[11px] font-semibold uppercase tracking-[0.09em] text-[#a32d1b]">
            Why reject this deck
          </label>
          <p className="mt-1 text-[11.5px] text-[#7a2b1c]/80">A reason is required and is recorded in the job log.</p>
          <Textarea
            id="reject-reason"
            className="mt-2.5 min-h-[80px] border-[#7a2b1c]/25 bg-paper-50"
            placeholder="What went wrong?"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            autoFocus
          />
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setRejectOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" disabled={!reason.trim() || reject.isPending} onClick={() => reject.mutate()}>
              {reject.isPending ? "Rejecting…" : "Confirm reject"}
            </Button>
          </div>
        </section>
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.42fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-6">
          <SlidePreview slides={artifact_urls.slides} index={index} onChange={setIndex}>
            <ImageGallery slides={artifact_urls.slides} index={index} onSelect={setIndex} />
          </SlidePreview>

          <section>
            <SectionHeading aside="1080 × 1350">Deck</SectionHeading>
            <Facts
              rows={[
                ["Slides", String(technical.slide_count)],
                ["Resolution", technical.resolution],
                ["Style preset", technical.style],
                ["Artifact size", `${(technical.total_size_bytes / 1024 / 1024).toFixed(2)} MB`],
                ["Plugin", job.plugin],
                ["Seed", String(job.seed)],
              ]}
            />
          </section>

          {job.plugin === "news_carousel" ? (
            <section>
              <SectionHeading aside={`${sources.length} cited`}>Sources</SectionHeading>
              {sources.length === 0 ? (
                <p className="text-[12.5px] text-ink-400">No sources recorded for this deck.</p>
              ) : (
                <ol className="flex flex-col">
                  {sources.map((source, sourceIndex) => {
                    const href = safeExternalUrl(source.url);
                    return (
                      <li
                        key={`${source.url}-${sourceIndex}`}
                        className="flex items-baseline gap-3 border-b border-ink-900/8 py-2 last:border-0"
                      >
                        <span className="fac tnum shrink-0 text-[9.5px]">{String(sourceIndex + 1).padStart(2, "0")}</span>
                        <div className="min-w-0">
                          <span className="block truncate text-[12.5px] font-medium text-ink-900">
                            {source.name ?? source.title ?? "Source"}
                          </span>
                          {href ? (
                            <a
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="block truncate text-[11px] text-ink-500 underline decoration-ink-900/25 underline-offset-2 transition-colors hover:text-ink-900 hover:decoration-ink-900"
                            >
                              {source.url}
                            </a>
                          ) : source.url ? (
                            <span className="block truncate text-[11px] text-ink-400">{source.url}</span>
                          ) : null}
                        </div>
                      </li>
                    );
                  })}
                </ol>
              )}
            </section>
          ) : null}
        </div>

        <div className="flex min-w-0 flex-col gap-6">
          <Card>
            <div className="flex items-baseline justify-between gap-3 border-b border-ink-900/10 px-4 py-3">
              <h2 className="text-[13px] font-semibold text-ink-900">Metadata</h2>
              <span className="fac text-[9.5px]">Editable</span>
            </div>
            <div className="p-4">
              <MetadataForm
                key={jobId}
                metadata={metadata}
                slideCount={slideCount}
                onSave={saveMetadata}
                onDirtyChange={setMetadataDirty}
              />
            </div>
          </Card>

          <Card>
            <div className="flex items-baseline justify-between gap-3 border-b border-ink-900/10 px-4 py-3">
              <h2 className="text-[13px] font-semibold text-ink-900">Provenance</h2>
              <span className="fac text-[9.5px]">Immutable</span>
            </div>
            <div className="p-4">
              <ProvenancePanel manifest={manifest} />
            </div>
          </Card>
        </div>
      </div>

      <div className="sticky bottom-0 z-20 -mx-5 border-t border-ink-900/12 bg-paper-100 px-5 py-3 sm:-mx-7 sm:px-7 lg:-mx-10 lg:px-10">
        <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <p className="text-[11.5px] text-ink-500">
            {metadataDirty ? (
              <span className="text-[#8f5413]">Unsaved metadata — use Save changes in Metadata before deciding.</span>
            ) : (
              <>
                Nothing publishes itself — approve when{" "}
                <span className="tnum font-semibold text-ink-900">{slideCount}</span> slides read right.
              </>
            )}
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setRejectOpen(true)} disabled={metadataDirty || busy}>
              <X className="h-3.5 w-3.5" /> Reject
            </Button>
            <Button onClick={() => approve.mutate()} disabled={metadataDirty || busy}>
              <Check className="h-3.5 w-3.5" /> {approve.isPending ? "Approving…" : "Approve"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
