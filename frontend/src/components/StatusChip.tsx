import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@/types";

type Variant = "default" | "outline" | "success" | "danger" | "blue";

/** Status speaks in the same spectrum as the pipeline: no new colour vocabulary. */
export const STATUS_META: Record<JobStatus, { variant: Variant; band: string; label: string }> = {
  QUEUED: { variant: "outline", band: "bg-spectrum-spec/70", label: "Queued" },
  RUNNING: { variant: "blue", band: "bg-spectrum-render", label: "Running" },
  REVIEW_READY: { variant: "default", band: "bg-ink-900", label: "Review ready" },
  APPROVED: { variant: "success", band: "bg-spectrum-export", label: "Approved" },
  REJECTED: { variant: "danger", band: "bg-signal", label: "Rejected" },
  FAILED: { variant: "danger", band: "bg-signal", label: "Failed" },
  CANCELLED: { variant: "outline", band: "bg-ink-400/40", label: "Cancelled" },
};

export function StatusChip({ status }: { status: JobStatus }) {
  const meta = STATUS_META[status];
  return <Badge variant={meta.variant}>{meta.label ?? status}</Badge>;
}
