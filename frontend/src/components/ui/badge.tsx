import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-[2px] px-1.5 py-[3px] text-[10.5px] font-semibold uppercase leading-none tracking-[0.08em] whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-ink-900 text-paper-50",
        outline: "border border-ink-900/20 text-ink-700",
        success: "bg-spectrum-export/12 text-[#1f7444]",
        danger: "bg-signal/12 text-[#a32d1b]",
        blue: "bg-spectrum-render/12 text-[#12708b]",
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
