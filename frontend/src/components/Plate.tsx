import type { ReactNode } from "react";
import { Link } from "react-router";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="mb-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-500 transition-colors hover:text-ink-900"
    >
      <ArrowLeft className="h-3.5 w-3.5" />
      {children}
    </Link>
  );
}

export function PlateHeader({
  title,
  meta,
  actions,
  back,
  className,
}: {
  title: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  back?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("border-b border-ink-900/12 pb-5", className)}>
      {back}
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <div className="min-w-0 basis-full sm:basis-0 sm:flex-1">
          <h1 className="text-[21px] font-semibold leading-[1.14] tracking-[-0.022em] text-ink-900 sm:text-[24px] lg:text-[26px]">{title}</h1>
          {meta ? <div className="mt-2 text-[12.5px] leading-relaxed text-ink-500">{meta}</div> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}

export function Facts({ rows, className }: { rows: [string, ReactNode][]; className?: string }) {
  return (
    <dl className={cn("flex flex-col", className)}>
      {rows.map(([label, value]) => (
        <div
          key={label}
          className="flex items-baseline justify-between gap-4 border-b border-ink-900/8 py-1.5 last:border-0"
        >
          <dt className="shrink-0 text-[12px] text-ink-400">{label}</dt>
          <dd className="tnum min-w-0 truncate text-right text-[12.5px] font-medium text-ink-900">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function SectionHeading({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 className="text-[13px] font-semibold tracking-[-0.005em] text-ink-900">{children}</h2>
      {aside ? <span className="tnum text-[11px] text-ink-400">{aside}</span> : null}
    </div>
  );
}
