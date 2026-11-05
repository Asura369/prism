import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SourceOption {
  name: string;
  label: string;
}

export function SourceToggleGroup({
  sources,
  selected,
  onChange,
}: {
  sources: SourceOption[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  function toggle(name: string) {
    onChange(selected.includes(name) ? selected.filter((item) => item !== name) : [...selected, name]);
  }

  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Trend sources">
      {sources.map((source) => {
        const active = selected.includes(source.name);
        return (
          <button
            key={source.name}
            type="button"
            aria-pressed={active}
            onClick={() => toggle(source.name)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-[3px] border px-2.5 py-1 text-[11.5px] font-medium transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60",
              active
                ? "border-ink-900 bg-ink-900 text-paper-50"
                : "border-ink-900/18 bg-paper-50 text-ink-500 hover:border-ink-900/35 hover:text-ink-900",
            )}
          >
            {active ? <Check className="h-3 w-3" /> : null}
            {source.label}
          </button>
        );
      })}
    </div>
  );
}
