import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@/types";

const VARIANTS: Record<JobStatus, "default" | "outline" | "ember" | "success" | "danger" | "amber" | "blue"> = {
  QUEUED: "outline",
  RUNNING: "blue",
  REVIEW_READY: "ember",
  APPROVED: "success",
  REJECTED: "danger",
  FAILED: "danger",
  CANCELLED: "outline",
};

const LABELS: Record<JobStatus, string> = {
  QUEUED: "Queued",
  RUNNING: "Running",
  REVIEW_READY: "Review ready",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
};

export function StatusChip({ status }: { status: JobStatus }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status] ?? status}</Badge>;
}
