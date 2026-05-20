import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu, LogOut, User, Bell, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/api/auth";
import { getApiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HeaderProps {
  onMenuToggle?: () => void;
  mobileMenuOpen?: boolean;
}

export function Header({ onMenuToggle, mobileMenuOpen }: HeaderProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await authApi.logout();
    } catch (err) {
      console.error(getApiErrorMessage(err));
    } finally {
      logout();
      navigate("/login");
      setLoggingOut(false);
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border/50 bg-background/80 px-4 backdrop-blur-xl lg:px-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onMenuToggle}
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
        <h1 className="text-sm font-medium text-muted-foreground lg:hidden">
          ComplianceGuard
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </Button>
        <div className="hidden items-center gap-2 rounded-lg border border-border/50 bg-card/50 px-3 py-1.5 sm:flex">
          <User className="h-4 w-4 text-cyan-400" aria-hidden />
          <div className="text-sm">
            <p className="font-medium leading-none">{user?.full_name}</p>
            <p className="text-xs text-muted-foreground">{user?.role?.replace(/_/g, " ")}</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleLogout}
          disabled={loggingOut}
          aria-label="Sign out"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Sign out</span>
        </Button>
      </div>
    </header>
  );
}

export function MobileNav({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const items = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/scans", label: "Scans" },
    { to: "/findings", label: "Findings" },
    { to: "/compliance", label: "Compliance" },
    { to: "/audit", label: "Audit Logs" },
    { to: "/settings", label: "Settings" },
  ];

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={onClose}
          aria-hidden
        />
      )}
      <nav
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 transform border-r border-border/50 bg-card transition-transform lg:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        aria-label="Mobile navigation"
      >
        <div className="flex h-16 items-center justify-between px-4 border-b border-border/50">
          <span className="font-semibold">Menu</span>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close menu">
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="space-y-1 p-4">
          {items.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              onClick={onClose}
              className="block rounded-lg px-3 py-2 text-sm hover:bg-accent"
            >
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </>
  );
}
