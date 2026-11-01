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
    <div className="flex flex-wrap gap-2" role="group" aria-label="Trend sources">
      {sources.map((source) => {
        const active = selected.includes(source.name);
        return (
          <button
            key={source.name}
            type="button"
            aria-pressed={active}
            onClick={() => toggle(source.name)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors",
              active
                ? "border-ink-900 bg-ink-900 text-cream-50"
                : "border-ink-900/15 bg-white/60 text-ink-500 hover:border-ink-900/30",
            )}
          >
            {active && <Check className="h-3 w-3" />}
            {source.label}
          </button>
        );
      })}
    </div>
  );
}
