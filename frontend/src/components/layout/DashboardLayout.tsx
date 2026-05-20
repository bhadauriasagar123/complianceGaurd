import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header, MobileNav } from "./Header";

export function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <MobileNav open={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="lg:pl-64">
        <Header
          mobileMenuOpen={mobileOpen}
          onMenuToggle={() => setMobileOpen((o) => !o)}
        />
        <main className="p-4 lg:p-6" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
