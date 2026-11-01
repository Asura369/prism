import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { DispatchAngle, PluginInfo } from "@/types";

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
    <Card className="flex h-full flex-col">
      <CardContent className="flex flex-1 flex-col gap-4 pt-6">
        <div className="flex items-center justify-between gap-3">
          <span className="eyebrow">Angle {index + 1}</span>
          <Badge variant="outline">{angle.target_emotion || "neutral"}</Badge>
        </div>

        <div>
          <h2 className="text-xl font-bold leading-snug text-ink-900">{angle.hook}</h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-500">{angle.framing}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{angle.format_suggestion}</Badge>
          <Badge variant="outline">{angle.est_slide_count} slides</Badge>
        </div>

        <p className="text-sm leading-relaxed text-ink-600">
          <span className="font-semibold text-ink-900">Why it works: </span>
          {angle.why_it_works}
        </p>

        <div className="rounded-xl border border-ink-900/10 bg-cream-100/70 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-400">Recommended plugin</p>
          <div className="mt-2 flex items-center justify-between gap-2">
            <Badge variant="ember">{angle.recommended_plugin}</Badge>
            <span className="text-[11px] text-ink-400">{angle.plugin_reasoning}</span>
          </div>
          <label className="mt-3 flex flex-col gap-1 text-[11px] font-semibold text-ink-500">
            Use plugin
            <select
              value={selectedPlugin}
              onChange={(event) => onPluginChange(event.target.value)}
              className="h-9 rounded-lg border border-ink-900/15 bg-white px-2 text-sm font-normal text-ink-900"
              aria-label={`Plugin for angle ${index + 1}`}
            >
              {plugins.map((plugin) => (
                <option key={plugin.name} value={plugin.name} disabled={!plugin.available}>
                  {plugin.name.replace("_carousel", "")} {plugin.available ? "" : "(unavailable)"}
                </option>
              ))}
            </select>
          </label>
        </div>

        <Button className="mt-auto w-full" onClick={onUse}>
          Use this angle <ArrowRight className="h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  );
}
