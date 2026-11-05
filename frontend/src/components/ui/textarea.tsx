import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[110px] w-full rounded-field border border-ink-900/18 bg-paper-50 px-3 py-2.5 text-[13.5px] leading-[1.6] text-ink-900 transition-colors placeholder:text-ink-400/90 hover:border-ink-900/30 focus-visible:border-ink-900/40 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";

export { Textarea };
