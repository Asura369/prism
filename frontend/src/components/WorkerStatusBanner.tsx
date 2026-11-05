import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
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
    <div className="flex items-start justify-between gap-4 border-b border-signal/25 bg-[#f7ece7] px-5 py-2.5 text-[12px] text-[#7a2b1c] sm:px-7 lg:px-10">
      <p className="leading-relaxed">
        <span className="font-semibold uppercase tracking-[0.08em]">Worker is not running</span>
        <span className="mx-2 text-[#7a2b1c]/40">/</span>
        Jobs will queue but not execute. Start it with{" "}
        <code className="rounded-[2px] bg-[#7a2b1c]/10 px-1 py-0.5 font-mono text-[11px]">make worker</code>.
      </p>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss worker warning"
        className="mt-px shrink-0 rounded-[2px] p-0.5 text-[#7a2b1c]/70 transition-colors hover:bg-[#7a2b1c]/10 hover:text-[#7a2b1c]"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
