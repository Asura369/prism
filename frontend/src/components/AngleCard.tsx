import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DispatchAngle, PluginInfo } from "@/types";

const BANDS = ["bg-spectrum-spec", "bg-spectrum-render", "bg-spectrum-publish"];

export function AngleCard({
  angle,
  index,
  plugins,
  selectedPlugin,
  onPluginChange,
  onUse,
}: {
  angle: DispatchAngle;
  index: number;
  plugins: PluginInfo[];
  selectedPlugin: string;
  onPluginChange: (plugin: string) => void;
  onUse: () => void;
}) {
  return (
    <article className="flex h-full flex-col rounded-plate border border-ink-900/12 bg-paper-50">
      <div className={`h-[3px] w-full ${BANDS[index % BANDS.length]}`} aria-hidden />

      <div className="flex flex-1 flex-col gap-4 p-5">
        <div className="flex items-baseline justify-between gap-3">
          <span className="fac tnum text-[10.5px] text-ink-400">{String(index + 1).padStart(2, "0")}</span>
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">
            {angle.target_emotion || "neutral"}
          </span>
        </div>

        <div>
          <h2 className="text-[17px] font-semibold leading-[1.25] tracking-[-0.015em] text-ink-900">
            {angle.hook}
          </h2>
          <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-500">{angle.framing}</p>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10.5px] uppercase tracking-[0.07em] text-ink-400">
          <span>{angle.format_suggestion}</span>
          <span aria-hidden>·</span>
          <span className="tnum">{angle.est_slide_count} slides</span>
        </div>

        <p className="text-[12.5px] leading-relaxed text-ink-500">
          <span className="font-semibold text-ink-900">Why it works </span>
          {angle.why_it_works}
        </p>

        <div className="mt-auto border-t border-ink-900/10 pt-3.5">
          <span className="fac text-[9.5px]">Route</span>
          <p className="mt-1 max-w-[46ch] text-[11.5px] leading-relaxed text-ink-500">{angle.plugin_reasoning}</p>
          <label className="mt-2 flex flex-col gap-1">
            <span className="sr-only">Plugin for angle {index + 1}</span>
            <select
              value={selectedPlugin}
              onChange={(event) => onPluginChange(event.target.value)}
              aria-label={`Plugin for angle ${index + 1}`}
              className="h-8 w-full rounded-field border border-ink-900/18 bg-paper-50 px-2.5 text-[12px] font-medium text-ink-900 transition-colors hover:border-ink-900/30 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60"
            >
              {plugins.map((plugin) => (
                <option key={plugin.name} value={plugin.name} disabled={!plugin.available}>
                  {plugin.name.replace("_carousel", "")} {plugin.available ? "" : "(unavailable)"}
                </option>
              ))}
            </select>
          </label>
        </div>

        <Button className="w-full" onClick={onUse}>
          Use this angle <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </article>
  );
}
