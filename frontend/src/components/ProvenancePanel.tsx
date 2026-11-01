import { Badge } from "@/components/ui/badge";

function read(value: unknown, path: string[]): unknown {
  let current: unknown = value;
  for (const key of path) {
    if (typeof current !== "object" || current === null) return undefined;
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

function text(value: unknown, fallback = "—"): string {
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback;
}

export function ProvenancePanel({ manifest }: { manifest: Record<string, unknown> }) {
  const adapters = read(manifest, ["adapters"]) as Record<string, Record<string, unknown>> | undefined;
  const retries = (read(manifest, ["retries"]) as unknown[] | undefined) ?? [];
  const hashes = (read(manifest, ["prompt_hashes"]) as Record<string, string> | undefined) ?? {};
  const fallbacks = (read(manifest, ["fallbacks_used"]) as string[] | undefined) ?? [];
  const degraded = Boolean(read(manifest, ["degraded"]));

  const rows: [string, string][] = [
    ["Plugin", `${text(read(manifest, ["plugin"]))} @ ${text(read(manifest, ["plugin_version"]))}`],
    ["LLM", `${text(adapters?.llm?.name)} · ${text(adapters?.llm?.model)}`],
    ["Renderer", `${text(adapters?.cards?.name)} · ${text(adapters?.cards?.style)}`],
    ["Export", text(adapters?.export?.name)],
    ["Retries", String(retries.length)],
    ["Sources", String(((read(manifest, ["sources"])) as unknown[] | undefined)?.length ?? 0)],
  ];

  return (
    <div className="flex flex-col gap-4">
      {degraded && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <Badge variant="amber">degraded</Badge>
          <span>Fallback adapter used: {fallbacks.join(", ") || "unknown"}</span>
        </div>
      )}
      <div className="flex flex-col gap-2 text-xs">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-start justify-between gap-4 border-b border-ink-900/5 pb-2 last:border-0">
            <span className="text-ink-400">{label}</span>
            <span className="text-right font-medium text-ink-900">{value}</span>
          </div>
        ))}
      </div>
      <details className="text-xs">
        <summary className="cursor-pointer font-semibold text-ink-500">Prompt hashes</summary>
        <div className="mt-2 flex flex-col gap-1 font-mono text-[10px] text-ink-400">
          {Object.entries(hashes).map(([name, hash]) => (
            <div key={name} className="flex justify-between gap-3">
              <span>{name}</span>
              <span title={hash}>{hash.slice(0, 16)}…</span>
            </div>
          ))}
          {Object.keys(hashes).length === 0 && <span>none recorded</span>}
        </div>
      </details>
    </div>
  );
}
