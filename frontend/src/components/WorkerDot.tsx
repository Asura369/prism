import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { cn } from "@/lib/utils";

export function WorkerDot() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 5000 });
  const alive = data?.worker.alive ?? false;
  return (
    <div className="flex items-center gap-2 text-[11.5px] text-ink-500" title="Worker status">
      <span
        className={cn(
          "h-[6px] w-[6px] shrink-0 rounded-full",
          alive ? "bg-spectrum-export" : "bg-ink-400/60",
        )}
        aria-hidden
      />
      <span className="truncate">{alive ? "Worker live" : "Worker offline"}</span>
    </div>
  );
}
