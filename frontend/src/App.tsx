import { NavLink, Outlet, Route, Routes } from "react-router-dom";
import { Compass, LayoutGrid, Plus, Settings as SettingsIcon, Puzzle } from "lucide-react";
import { WorkerStatusBanner } from "@/components/WorkerStatusBanner";
import { WorkerDot } from "@/components/WorkerDot";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import Dashboard from "@/pages/Dashboard";
import Discover from "@/pages/Discover";
import NewJob from "@/pages/NewJob";
import JobDetail from "@/pages/JobDetail";
import Review from "@/pages/Review";
import Plugins from "@/pages/Plugins";
import Settings from "@/pages/Settings";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutGrid, end: true },
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/plugins", label: "Plugins", icon: Puzzle },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

function Layout() {
  return (
    <div className="min-h-screen bg-cream-50">
      <WorkerStatusBanner />
      <div className="flex">
        <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-ink-900/10 bg-cream-100/60 px-5 py-7">
          <div className="px-2">
            <div
              className="text-2xl font-bold tracking-tight text-ink-900"
              title="A human-in-the-loop content automation framework."
            >
              Prism
            </div>
            <p className="mt-1 text-[11px] leading-snug text-ink-400">
              Human-in-the-loop
              <br />
              content automation
            </p>
          </div>

          <nav className="mt-9 flex flex-col gap-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive ? "bg-ink-900 text-cream-50" : "text-ink-500 hover:bg-ink-900/5 hover:text-ink-900",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-xl border border-ink-900/10 bg-white/50 p-3 text-[11px] leading-relaxed text-ink-400">
            Render, review, approve. Nothing publishes itself.
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-ink-900/10 bg-cream-50/85 px-8 backdrop-blur">
            <span className="eyebrow">{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</span>
            <div className="flex items-center gap-5">
              <WorkerDot />
              <Button asChild size="sm" variant="ember">
                <NavLink to="/new">
                  <Plus className="h-3.5 w-3.5" /> New job
                </NavLink>
              </Button>
            </div>
          </header>
          <main className="mx-auto w-full max-w-[1180px] flex-1 px-8 py-9">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="discover" element={<Discover />} />
        <Route path="new" element={<NewJob />} />
        <Route path="jobs/:jobId" element={<JobDetail />} />
        <Route path="review/:jobId" element={<Review />} />
        <Route path="plugins" element={<Plugins />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<div className="text-ink-500">Page not found.</div>} />
      </Route>
    </Routes>
  );
}
