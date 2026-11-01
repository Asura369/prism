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
    <div className="flex gap-2.5 overflow-x-auto pb-2" role="listbox" aria-label="Slides">
      {slides.map((src, slideIndex) => (
        <button
          key={src}
          type="button"
          role="option"
          aria-selected={slideIndex === index}
          aria-label={`Slide ${slideIndex + 1}`}
          onClick={() => onSelect(slideIndex)}
          className={cn(
            "relative w-20 shrink-0 overflow-hidden rounded-lg border-2 transition-all",
            slideIndex === index ? "border-ember-500 ring-2 ring-ember-500/20" : "border-transparent opacity-70 hover:opacity-100",
          )}
        >
          <img src={src} alt="" className="aspect-[4/5] w-full object-cover" loading="lazy" />
          <span className="absolute bottom-1 left-1 rounded bg-ink-900/70 px-1 text-[10px] font-semibold text-white">
            {slideIndex + 1}
          </span>
        </button>
      ))}
    </div>
  );
}
