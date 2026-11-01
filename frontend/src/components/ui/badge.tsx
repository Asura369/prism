import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide",
  {
    variants: {
      variant: {
        default: "border-transparent bg-ink-900 text-cream-50",
        outline: "border-ink-900/15 text-ink-700",
        ember: "border-transparent bg-ember-500/12 text-ember-600",
        success: "border-transparent bg-emerald-600/12 text-emerald-700",
        danger: "border-transparent bg-red-600/10 text-red-700",
        amber: "border-transparent bg-amber-500/15 text-amber-700",
        blue: "border-transparent bg-sky-600/10 text-sky-700",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
