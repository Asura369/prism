import { cn } from "@/lib/utils";

export function ImageGallery({
  slides,
  index,
  onSelect,
}: {
  slides: string[];
  index: number;
  onSelect: (index: number) => void;
}) {
  return (
    <div className="flex gap-1.5 overflow-x-auto pb-1" role="listbox" aria-label="Slides">
      {slides.map((src, slideIndex) => {
        const active = slideIndex === index;
        return (
          <button
            key={src}
            type="button"
            role="option"
            aria-selected={active}
            aria-label={`Slide ${slideIndex + 1}`}
            onClick={() => onSelect(slideIndex)}
            className={cn(
              "relative w-[58px] shrink-0 overflow-hidden border p-0 transition-opacity duration-150 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-paper-50",
              active ? "border-paper-50 opacity-100" : "border-gate-700 opacity-60 hover:opacity-90",
            )}
          >
            <img src={src} alt="" className="aspect-[4/5] w-full object-cover" loading="lazy" />
            <span className="fac absolute bottom-0 left-0 bg-gate-900/85 px-1 py-px text-[9px] text-paper-50">
              {String(slideIndex + 1).padStart(2, "0")}
            </span>
          </button>
        );
      })}
    </div>
  );
}
