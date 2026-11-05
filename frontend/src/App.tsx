import { NavLink, Outlet, Route, Routes } from "react-router";
import { Compass, LayoutGrid, Plus, Puzzle, SlidersHorizontal } from "lucide-react";
import { WorkerStatusBanner } from "@/components/WorkerStatusBanner";
import { WorkerDot } from "@/components/WorkerDot";
import { PlateHeader } from "@/components/Plate";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import Dashboard from "@/pages/Dashboard";
import Discover from "@/pages/Discover";
import Angles from "@/pages/Angles";
import NewJob from "@/pages/NewJob";
import JobDetail from "@/pages/JobDetail";
import Review from "@/pages/Review";
import Plugins from "@/pages/Plugins";
import Settings from "@/pages/Settings";

const NAV = [
  { to: "/", label: "Queue", icon: LayoutGrid, end: true, folio: "01" },
  { to: "/discover", label: "Discover", icon: Compass, folio: "02" },
  { to: "/plugins", label: "Plugins", icon: Puzzle, folio: "03" },
  { to: "/settings", label: "Settings", icon: SlidersHorizontal, folio: "04" },
];

function Mark() {
  return (
    <svg viewBox="0 0 24 24" className="h-[22px] w-[22px] shrink-0" fill="none" aria-hidden>
      <path d="M12 3.2 21.2 19.4H2.8Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M0.4 11.6h6.8" stroke="currentColor" strokeWidth="1.3" />
      <path d="M16.7 11.6 23.6 6.9" stroke="#4B32C3" strokeWidth="1.3" />
      <path d="M16.7 12 23.6 12" stroke="#2E9E5B" strokeWidth="1.3" />
      <path d="M16.7 12.4 23.6 17.1" stroke="#A32250" strokeWidth="1.3" />
    </svg>
  );
}

function NavItem({ to, label, icon: Icon, end, folio, compact }: (typeof NAV)[number] & { compact?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      aria-label={compact ? label : undefined}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 rounded-[3px] px-2.5 text-[13px] transition-colors",
          compact ? "h-8 px-2" : "h-9",
          isActive
            ? "bg-ink-900 text-paper-50"
            : "text-ink-500 hover:bg-ink-900/[0.055] hover:text-ink-900",
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className="h-[15px] w-[15px] shrink-0" strokeWidth={1.6} />
          <span className={cn("truncate font-medium", compact ? "hidden sm:inline" : "flex-1")}>{label}</span>
          {!compact ? (
            <span className={cn("fac text-[9.5px]", isActive ? "text-paper-50/45" : "text-ink-400/60")}>{folio}</span>
          ) : null}
        </>
      )}
    </NavLink>
  );
}

function Layout() {
  return (
    <div className="min-h-screen bg-paper-100">
      <div className="lg:flex">
        <aside className="sticky top-0 hidden h-screen w-[236px] shrink-0 flex-col border-r border-ink-900/12 px-4 py-5 lg:flex">
          <NavLink to="/" className="mb-7 flex items-start gap-2.5 px-1 text-ink-900" aria-label="Prism — queue">
            <Mark />
            <span className="min-w-0">
              <span className="block text-[15px] font-semibold leading-tight tracking-[-0.015em]">Prism</span>
              <span className="mt-0.5 block text-[10.5px] leading-[1.35] text-ink-400">
                Human-in-the-loop
                <br />
                content automation
              </span>
            </span>
          </NavLink>

          <nav className="flex flex-col gap-0.5" aria-label="Sections">
            {NAV.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
          </nav>

          <div className="mt-auto flex flex-col gap-3 px-1">
            <WorkerDot />
            <div className="rule" />
            <p className="text-[10.5px] leading-[1.45] text-ink-400">Nothing publishes itself.</p>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3 border-b border-ink-900/12 px-4 py-3 lg:hidden">
            <NavLink to="/" className="flex items-center gap-2 text-ink-900" aria-label="Prism — queue">
              <Mark />
              <span className="text-[14px] font-semibold tracking-[-0.015em]">Prism</span>
            </NavLink>
            <nav className="ml-2 flex items-center gap-1 overflow-x-auto" aria-label="Sections">
              {NAV.map((item) => (
                <NavItem key={item.to} {...item} compact />
              ))}
            </nav>
          </div>

          <WorkerStatusBanner />

          <main className="mx-auto w-full max-w-[1240px] px-5 pb-24 pt-7 sm:px-7 lg:px-10 lg:pb-16 lg:pt-9">
            <Outlet />
          </main>
        </div>
      </div>

    </div>
  );
}

function NotFound() {
  return (
    <PlateHeader
      title="Page not found."
      meta="That route isn't part of this build. The queue is where the work is."
      actions={
        <Button asChild>
          <NavLink to="/">
            <Plus className="h-3.5 w-3.5" /> Back to the queue
          </NavLink>
        </Button>
      }
    />
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="discover" element={<Discover />} />
        <Route path="discover/angles" element={<Angles />} />
        <Route path="new" element={<NewJob />} />
        <Route path="jobs/:jobId" element={<JobDetail />} />
        <Route path="review/:jobId" element={<Review />} />
        <Route path="plugins" element={<Plugins />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
