import { useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SlidePreview({
  slides,
  index,
  onChange,
}: {
  slides: string[];
  index: number;
  onChange: (index: number) => void;
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
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-card border border-ink-900/10 bg-cream-100 shadow-card">
        <img
          src={slides[index]}
          alt={`Slide ${index + 1} of ${slides.length}`}
          className="mx-auto max-h-[620px] w-auto object-contain"
        />
        <div className="absolute bottom-3 right-3 flex items-center gap-2 rounded-full bg-ink-900/80 px-2 py-1 text-white backdrop-blur">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-white hover:bg-white/15"
            onClick={() => onChange(Math.max(0, index - 1))}
            aria-label="Previous slide"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-10 text-center text-[11px] font-semibold">
            {index + 1} / {slides.length}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-white hover:bg-white/15"
            onClick={() => onChange(Math.min(slides.length - 1, index + 1))}
            aria-label="Next slide"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <p className="text-center text-[11px] text-ink-400">Use ← → to move between slides.</p>
    </div>
  );
}
