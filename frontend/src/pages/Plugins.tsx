import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { PlateHeader } from "@/components/Plate";
import { Badge } from "@/components/ui/badge";

export default function Plugins() {
  const { data = [], isLoading, error } = useQuery({ queryKey: ["plugins"], queryFn: api.plugins });

  return (
    <div className="flex flex-col gap-6">
      <PlateHeader
        title="Installed formats"
        meta="Plugins share the carousel base and diverge on spec schema, slide structure, and policy. That divergence is the product."
      />

      {error ? <p className="text-[12.5px] text-[#a32d1b]">{(error as Error).message}</p> : null}

      {isLoading ? (
        <div className="h-40 animate-pulse rounded-plate border border-ink-900/10 bg-paper-50" />
      ) : (
        <div className="overflow-x-auto rounded-plate border border-ink-900/12 bg-paper-50">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="border-b border-ink-900/12">
                {["Format", "Version", "Output", "Default style", "Slides", "Adapters"].map((label) => (
                  <th
                    key={label}
                    scope="col"
                    className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-400"
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((plugin) => {
                const defaults = plugin.defaults as Record<string, unknown>;
                return (
                  <tr key={plugin.name} className="border-b border-ink-900/8 last:border-0">
                    <th scope="row" className="px-4 py-3.5 align-top">
                      <span className="block text-[13px] font-semibold text-ink-900">
                        {plugin.name.replace("_carousel", "")}
                      </span>
                      <span className="mt-0.5 block max-w-[38ch] text-[11.5px] font-normal leading-relaxed text-ink-500">
                        {plugin.description}
                      </span>
                    </th>
                    <td className="tnum px-4 py-3.5 align-top text-[12px] text-ink-700">{plugin.version}</td>
                    <td className="px-4 py-3.5 align-top text-[12px] text-ink-700">{plugin.output_kind}</td>
                    <td className="px-4 py-3.5 align-top text-[12px] text-ink-700">{String(defaults.style ?? "—")}</td>
                    <td className="tnum px-4 py-3.5 align-top text-[12px] text-ink-700">
                      {String(defaults.slide_count ?? "—")}
                    </td>
                    <td className="px-4 py-3.5 align-top">
                      {plugin.available ? (
                        <Badge variant="success">available</Badge>
                      ) : (
                        <div className="flex flex-col items-start gap-1">
                          <Badge variant="danger">unavailable</Badge>
                          <span className="text-[10.5px] text-[#a32d1b]">
                            Missing: {plugin.missing_adapters.join(", ")}
                          </span>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="max-w-[70ch] text-[11.5px] leading-relaxed text-ink-400">
        Every format renders through the same pipeline and lands in the queue with an immutable provenance manifest.
      </p>
    </div>
  );
}
