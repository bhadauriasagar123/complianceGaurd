import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ScanSearch,
  AlertTriangle,
  Shield,
  ScrollText,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/scans", label: "Scans", icon: ScanSearch },
  { to: "/findings", label: "Findings", icon: AlertTriangle },
  { to: "/compliance", label: "Compliance", icon: Shield },
  { to: "/audit", label: "Audit Logs", icon: ScrollText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside
      className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-border/50 bg-card/30 backdrop-blur-xl lg:flex"
      aria-label="Main navigation"
    >
      <div className="flex h-16 items-center gap-2 border-b border-border/50 px-6">
        <ShieldCheck className="h-8 w-8 text-cyan-400" aria-hidden />
        <span className="font-semibold tracking-tight text-foreground">
          Compliance<span className="text-cyan-400">Guard</span>
        </span>
      </div>
      <nav className="flex-1 space-y-1 p-4" role="navigation">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border/50 p-4">
        <p className="text-xs text-muted-foreground">v1.0.0 · Secure by design</p>
      </div>
    </aside>
  );
}
