import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { cn } from "@/lib/utils";

export function WorkerDot() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });
  const alive = data?.worker.alive ?? false;
  return (
    <div className="flex items-center gap-2 text-xs text-ink-500" title="Worker status">
      <span
        className={cn("h-2 w-2 rounded-full", alive ? "bg-emerald-500" : "bg-ink-400/50")}
        aria-hidden
      />
      <span>{alive ? "Worker live" : "Worker offline"}</span>
    </div>
  );
}
