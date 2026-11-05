import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-[3px] text-[13px] font-medium transition-colors duration-150 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ink-900/70 disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        default: "bg-ink-900 text-paper-50 hover:bg-ink-700",
        outline:
          "border border-ink-900/20 bg-transparent text-ink-900 hover:border-ink-900/45 hover:bg-ink-900/[0.04]",
        ghost: "text-ink-700 hover:bg-ink-900/[0.06] hover:text-ink-900",
        signal: "bg-signal text-paper-50 hover:brightness-95",
        destructive: "bg-signal text-paper-50 hover:brightness-95",
      },
      size: {
        default: "h-9 px-3.5",
        sm: "h-8 px-3 text-[12px]",
        lg: "h-11 px-5 text-[14px]",
        icon: "h-8 w-8",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
