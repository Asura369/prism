import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Plugins() {
  const { data = [], isLoading, error } = useQuery({ queryKey: ["plugins"], queryFn: api.plugins });

  return (
    <div className="flex flex-col gap-7">
      <div>
        <p className="eyebrow">Plugins</p>
        <h1 className="page-title mt-2">Installed carousel formats</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-500">
          Plugins share the carousel base and diverge on spec schema, slide structure, and policy.
        </p>
      </div>
      {error && <p className="text-sm text-red-700">{(error as Error).message}</p>}
      {isLoading && <p className="text-sm text-ink-500">Loading plugins…</p>}
      <div className="grid gap-5 md:grid-cols-2">
        {data.map((plugin) => {
          const defaults = plugin.defaults as Record<string, unknown>;
          return (
            <Card key={plugin.name}>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle>{plugin.name}</CardTitle>
                  <Badge variant={plugin.available ? "success" : "danger"}>
                    {plugin.available ? "available" : "unavailable"}
                  </Badge>
                </div>
                <CardDescription>{plugin.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-ink-400">Version</span>
                  <span className="font-medium">{plugin.version}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-ink-400">Output</span>
                  <span className="font-medium">{plugin.output_kind}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-ink-400">Default style</span>
                  <span className="font-medium">{String(defaults.style ?? "—")}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-ink-400">Default slides</span>
                  <span className="font-medium">{String(defaults.slide_count ?? "—")}</span>
                </div>
                <div className="rule my-1" />
                {plugin.available ? (
                  <p className="flex items-center gap-2 text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" /> Required adapters present
                  </p>
                ) : (
                  <p className="flex items-center gap-2 text-red-700">
                    <XCircle className="h-4 w-4" /> Missing: {plugin.missing_adapters.join(", ")}
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
