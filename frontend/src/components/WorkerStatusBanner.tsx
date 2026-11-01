import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, X } from "lucide-react";
import { api } from "@/api/client";

export function WorkerStatusBanner() {
  const [dismissed, setDismissed] = useState(false);
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 5000,
  });

  if (!data || data.worker.alive || dismissed) return null;

  return (
    <div className="flex items-center justify-between gap-4 border-b border-amber-300/60 bg-amber-50 px-6 py-2.5 text-sm text-amber-900">
      <div className="flex items-center gap-2.5">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>
          Worker is not running. Jobs will queue but not execute. Start it with{" "}
          <code className="rounded bg-amber-900/10 px-1.5 py-0.5 font-mono text-xs">make worker</code>.
        </span>
      </div>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss worker warning"
        className="rounded-full p-1 hover:bg-amber-900/10"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
