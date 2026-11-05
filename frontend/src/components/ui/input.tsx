import * as React from "react";
import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-9 w-full rounded-field border border-ink-900/18 bg-paper-50 px-3 text-[13.5px] text-ink-900 transition-colors placeholder:text-ink-400/90 hover:border-ink-900/30 focus-visible:border-ink-900/40 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/60 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
