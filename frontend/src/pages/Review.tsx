import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, Download, RotateCcw, X } from "lucide-react";
import { api } from "@/api/client";
import { ImageGallery } from "@/components/ImageGallery";
import { MetadataForm } from "@/components/MetadataForm";
import { ProvenancePanel } from "@/components/ProvenancePanel";
import { SlidePreview } from "@/components/SlidePreview";
import { StatusChip } from "@/components/StatusChip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
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

  if (reviewQuery.isLoading) return <p className="text-sm text-ink-500">Loading review…</p>;
  if (reviewQuery.isError || !reviewQuery.data) {
    return (
      <div className="flex flex-col gap-4">
        <Link to="/" className="flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900">
          <ArrowLeft className="h-4 w-4" /> Dashboard
        </Link>
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
              <Badge variant="outline">{job.plugin}</Badge>
            </div>
            <h1 className="page-title mt-2 max-w-2xl">{metadata.title || job.topic}</h1>
            <p className="mt-2 text-sm text-ink-500">Review the deck, edit the metadata, then approve or reject.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <a href={artifact_urls.download} download>
                <Download className="h-4 w-4" /> Download
              </a>
            </Button>
            <Button variant="outline" onClick={() => regenerate.mutate()} disabled={regenerate.isPending}>
              <RotateCcw className="h-4 w-4" /> Regenerate
            </Button>
            <Button variant="outline" onClick={() => setRejectOpen(true)}>
              <X className="h-4 w-4" /> Reject
            </Button>
            <Button variant="ember" onClick={() => approve.mutate()} disabled={approve.isPending}>
              <Check className="h-4 w-4" /> {approve.isPending ? "Approving…" : "Approve"}
            </Button>
          </div>
        </div>
      </div>

      {actionError && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{actionError}</p>
      )}

      <div className="grid gap-7 lg:grid-cols-[1.25fr_1fr]">
        <div className="flex flex-col gap-5">
          <ImageGallery slides={artifact_urls.slides} index={index} onSelect={setIndex} />
          <SlidePreview slides={artifact_urls.slides} index={index} onChange={setIndex} />

          <Card>
            <CardHeader>
              <CardTitle>Deck details</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              {[
                ["Slides", String(technical.slide_count)],
                ["Resolution", technical.resolution],
                ["Style preset", technical.style],
                ["Artifact size", `${(technical.total_size_bytes / 1024 / 1024).toFixed(2)} MB`],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-4 border-b border-ink-900/5 pb-2 last:border-0">
                  <span className="text-ink-400">{label}</span>
                  <span className="font-medium text-ink-900">{value}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          {job.plugin === "news_carousel" && (
            <Card>
              <CardHeader>
                <CardTitle>Sources</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 text-sm">
                {sources.length === 0 && <p className="text-ink-400">No sources recorded.</p>}
                {sources.map((source, sourceIndex) => (
                  <div key={`${source.url}-${sourceIndex}`} className="flex flex-col gap-0.5">
                    <span className="font-medium text-ink-900">{source.name ?? "Source"}</span>
                    {source.url ? (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate text-xs text-ember-600 underline underline-offset-2"
                      >
                        {source.url}
                      </a>
                    ) : null}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-5">
          <Card>
            <CardHeader>
              <CardTitle>Metadata</CardTitle>
            </CardHeader>
            <CardContent>
              <MetadataForm
                key={jobId}
                metadata={metadata}
                slideCount={slideCount}
                onSave={saveMetadata}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Provenance</CardTitle>
            </CardHeader>
            <CardContent>
              <ProvenancePanel manifest={manifest} />
            </CardContent>
          </Card>
        </div>
      </div>

      {rejectOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-6" role="dialog" aria-modal>
          <div className="w-full max-w-md rounded-card border border-ink-900/10 bg-cream-50 p-6 shadow-card">
            <h2 className="text-lg font-bold">Reject this deck</h2>
            <p className="mt-1 text-sm text-ink-500">A reason is required and gets recorded in the job log.</p>
            <Textarea
              className="mt-4"
              placeholder="What went wrong?"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              aria-label="Rejection reason"
            />
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setRejectOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={!reason.trim() || reject.isPending}
                onClick={() => reject.mutate()}
              >
                {reject.isPending ? "Rejecting…" : "Confirm reject"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
