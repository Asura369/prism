import { cn } from "@/lib/utils";
import type { Stage } from "@/types";

export const STAGE_BANDS: Record<string, { label: string; fill: string; track: string; ink: string }> = {
  spec: { label: "Spec", fill: "bg-spectrum-spec", track: "bg-spectrum-spec/20", ink: "text-spectrum-spec" },
  ingest: { label: "Ingest", fill: "bg-spectrum-ingest", track: "bg-spectrum-ingest/20", ink: "text-spectrum-ingest" },
  render: { label: "Render", fill: "bg-spectrum-render", track: "bg-spectrum-render/20", ink: "text-spectrum-render" },
  export: { label: "Export", fill: "bg-spectrum-export", track: "bg-spectrum-export/20", ink: "text-spectrum-export" },
  metadata: { label: "Metadata", fill: "bg-spectrum-metadata", track: "bg-spectrum-metadata/20", ink: "text-spectrum-metadata" },
  policy: { label: "Policy", fill: "bg-spectrum-policy", track: "bg-spectrum-policy/20", ink: "text-spectrum-policy" },
  validate: { label: "Validate", fill: "bg-spectrum-validate", track: "bg-spectrum-validate/20", ink: "text-spectrum-validate" },
  publish: { label: "Publish", fill: "bg-spectrum-publish", track: "bg-spectrum-publish/20", ink: "text-spectrum-publish" },
};

const FALLBACK = { label: "", fill: "bg-ink-400", track: "bg-ink-900/10", ink: "text-ink-500" };

export function stageBand(name: string) {
  return STAGE_BANDS[name] ?? { ...FALLBACK, label: name };
}

/** The pipeline as one dispersed band: each stage is a cell, filled by its own progress. */
export function StageSpectrum({ stages }: { stages: Stage[] }) {
  return (
    <ol className="grid grid-cols-2 gap-px overflow-hidden rounded-plate border border-ink-900/12 bg-ink-900/12 sm:grid-cols-4 lg:grid-cols-[repeat(auto-fit,minmax(104px,1fr))]">
      {stages.map((stage) => {
        const band = stageBand(stage.name);
        const done = stage.status === "completed";
        const active = stage.status === "running";
        const failed = stage.status === "failed";
        const pct = done ? 100 : Math.round((stage.progress ?? 0) * 100);
        return (
          <li key={stage.name} className="bg-paper-50 px-2.5 pb-2 pt-2.5">
            <div className={cn("relative h-[3px] w-full overflow-hidden", band.track)}>
              <div
                className={cn("h-full transition-[width] duration-500 motion-reduce:transition-none", failed ? "bg-signal" : band.fill)}
                style={{ width: `${failed ? 100 : pct}%` }}
              />
            </div>
            <div className="mt-2 flex items-center justify-between gap-1">
              <span
                className={cn(
                  "text-[11px] font-semibold leading-none",
                  active ? "text-ink-900" : failed ? "text-signal" : done ? "text-ink-700" : "text-ink-400",
                )}
              >
                {band.label}
              </span>
              {active ? (
                <span className={cn("h-1.5 w-1.5 animate-pulse rounded-full motion-reduce:animate-none", band.fill)} />
              ) : null}
            </div>
            <span className="fac mt-1 block text-[9.5px] tracking-[0.1em]">
              {done ? "done" : active ? `${pct}%` : failed ? "failed" : "queued"}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export interface DispersionSegment {
  key: string;
  label: string;
  count: number;
  fill: string;
}

/** Today's run, split by state. Widths are counts, so the strip is a real readout. */
export function DispersionBar({ segments }: { segments: DispersionSegment[] }) {
  const shown = segments.filter((segment) => segment.count > 0);
  const total = shown.reduce((sum, segment) => sum + segment.count, 0);
  if (total === 0) return null;

  return (
    <div>
      <div className="flex h-[10px] w-full gap-px overflow-hidden rounded-[2px] border border-ink-900/20 bg-paper-200">
        {shown.map((segment) => (
          <div
            key={segment.key}
            className={cn(segment.fill, "h-full min-w-[3px]")}
            style={{ flexGrow: segment.count }}
            title={`${segment.label}: ${segment.count}`}
          />
        ))}
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-5 gap-y-1.5">
        {shown.map((segment) => (
          <span key={segment.key} className="flex items-center gap-1.5 text-[11.5px] text-ink-500">
            <span className={cn("h-[6px] w-[6px] rounded-full", segment.fill)} aria-hidden />
            <span className="tnum font-semibold text-ink-900">{segment.count}</span>
            {segment.label}
          </span>
        ))}
      </div>
    </div>
  );
}
