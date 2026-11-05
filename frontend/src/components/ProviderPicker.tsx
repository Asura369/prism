import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ProviderInfo } from "@/types";

export function ProviderPicker({
  providers,
  selected,
  onSelect,
}: {
  providers: ProviderInfo[];
  selected: string | null;
  onSelect: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const current = providers.find((provider) => provider.name === selected);

  return (
    <div className="relative inline-block" ref={ref}>
      <Button
        size="sm"
        variant="outline"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {current ? current.label : "Choose a provider"}
        <ChevronDown className="size-3.5" aria-hidden />
      </Button>

      {open ? (
        <div
          role="listbox"
          aria-label="Model providers"
          className="absolute z-20 mt-1 w-60 rounded-plate border border-ink-900/12 bg-paper-50 py-1 shadow-[0_8px_24px_rgba(15,15,15,0.08)]"
        >
          {providers.map((provider) => (
            <button
              key={provider.name}
              type="button"
              role="option"
              aria-selected={provider.name === selected}
              onClick={() => {
                onSelect(provider.name);
                setOpen(false);
              }}
              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-[12.5px] text-ink-700 hover:bg-ink-900/[0.05] aria-selected:bg-ink-900/[0.05] aria-selected:font-medium aria-selected:text-ink-900"
            >
              <span>{provider.label}</span>
              <span className="font-mono text-[10.5px] text-ink-400">{provider.name}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
