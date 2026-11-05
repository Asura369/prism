import { useEffect, type ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function SlidePreview({
  slides,
  index,
  onChange,
  children,
}: {
  slides: string[];
  index: number;
  onChange: (index: number) => void;
  children?: ReactNode;
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.target instanceof HTMLElement && ["INPUT", "TEXTAREA"].includes(event.target.tagName)) return;
      if (event.key === "ArrowLeft") onChange(Math.max(0, index - 1));
      if (event.key === "ArrowRight") onChange(Math.min(slides.length - 1, index + 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, onChange, slides.length]);

  if (slides.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-plate border border-ink-900/12 bg-gate-900">
      <div className="relative flex min-h-[300px] items-center justify-center p-4 sm:p-6">
        <img
          src={slides[index]}
          alt={`Slide ${index + 1} of ${slides.length}`}
          className="max-h-[36vh] w-auto max-w-full object-contain ring-1 ring-paper-50/15 sm:max-h-[54vh]"
        />
        <div className="absolute bottom-3 right-3 flex items-center gap-1 rounded-[2px] bg-gate-800/95 px-1 py-1">
          <button
            type="button"
            onClick={() => onChange(Math.max(0, index - 1))}
            aria-label="Previous slide"
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-[2px] text-paper-50/80 transition-colors hover:bg-gate-700 hover:text-paper-50",
              "focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-paper-50",
            )}
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="tnum min-w-9 text-center text-[10.5px] font-semibold text-paper-50">
            {index + 1} / {slides.length}
          </span>
          <button
            type="button"
            onClick={() => onChange(Math.min(slides.length - 1, index + 1))}
            aria-label="Next slide"
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-[2px] text-paper-50/80 transition-colors hover:bg-gate-700 hover:text-paper-50",
              "focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-paper-50",
            )}
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      {children ? <div className="border-t border-gate-700/80 px-3 pb-3 pt-3 sm:px-4">{children}</div> : null}
    </div>
  );
}
