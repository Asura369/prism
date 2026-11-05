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
    <div className="flex flex-col gap-3">
      {degraded ? (
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 border border-signal/30 bg-signal/[0.06] px-2.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#a32d1b]">Degraded</span>
          <span className="text-[11.5px] text-[#7a2b1c]">
            Fallback adapter used: {fallbacks.join(", ") || "unknown"}
          </span>
        </div>
      ) : null}

      <dl className="flex flex-col">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex items-baseline justify-between gap-4 border-b border-ink-900/8 py-1.5 last:border-0"
          >
            <dt className="shrink-0 text-[12px] text-ink-400">{label}</dt>
            <dd className="min-w-0 truncate text-right text-[12px] font-medium text-ink-900">{value}</dd>
          </div>
        ))}
      </dl>

      <details className="group border-t border-ink-900/10 text-[12px]">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 pt-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-400 transition-colors hover:text-ink-900">
          Prompt hashes
          <span className="text-[10px] transition-transform group-open:rotate-90 motion-reduce:transition-none">›</span>
        </summary>
        <div className="mt-2 flex flex-col gap-1 font-mono text-[10px] text-ink-400">
          {Object.entries(hashes).map(([name, hash]) => (
            <div key={name} className="flex justify-between gap-3">
              <span className="truncate">{name}</span>
              <span className="shrink-0" title={hash}>
                {hash.slice(0, 16)}…
              </span>
            </div>
          ))}
          {Object.keys(hashes).length === 0 ? <span>none recorded</span> : null}
        </div>
      </details>
    </div>
  );
}
