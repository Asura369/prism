import { Check, Circle, Loader2, X } from "lucide-react";
import type { Stage } from "@/types";
import { cn } from "@/lib/utils";

const LABELS: Record<string, string> = {
  spec: "Spec",
  ingest: "Ingest",
  render: "Render",
  export: "Export",
  metadata: "Metadata",
  policy: "Policy",
  validate: "Validate",
  publish: "Publish",
};

export function StageStepper({ stages }: { stages: Stage[] }) {
  return (
    <ol className="flex flex-wrap items-start gap-y-4">
      {stages.map((stage, index) => {
        const done = stage.status === "completed";
        const active = stage.status === "running";
        const failed = stage.status === "failed";
        return (
          <li key={stage.name} className="flex min-w-[86px] flex-1 items-start">
            <div className="flex w-full flex-col items-center gap-2 text-center">
              <div className="flex w-full items-center">
                <div
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[11px]",
                    done && "border-emerald-600 bg-emerald-600 text-white",
                    active && "border-ember-500 bg-ember-500/10 text-ember-600",
                    failed && "border-red-500 bg-red-500/10 text-red-600",
                    !done && !active && !failed && "border-ink-900/15 text-ink-400",
                  )}
                >
                  {done ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : active ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : failed ? (
                    <X className="h-3.5 w-3.5" />
                  ) : (
                    <Circle className="h-2.5 w-2.5" />
                  )}
                </div>
                {index < stages.length - 1 && (
                  <div className={cn("mx-1 h-px flex-1", done ? "bg-emerald-600/40" : "bg-ink-900/10")} />
                )}
              </div>
              <span
                className={cn(
                  "text-[11px] font-semibold",
                  active ? "text-ink-900" : failed ? "text-red-600" : "text-ink-400",
                )}
              >
                {LABELS[stage.name] ?? stage.name}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
