import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ShieldCheck, Zap, Brain, Lock, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: ShieldCheck,
    title: "Multi-Framework Compliance",
    description: "HIPAA, GDPR, PCI-DSS, and OWASP mapped automatically from scan findings.",
  },
  {
    icon: Brain,
    title: "AI-Powered Remediation",
    description: "Context-aware fix recommendations with confidence scoring for every finding.",
  },
  {
    icon: Zap,
    title: "Real-Time Scanning",
    description: "Nmap, Nuclei, ZAP, and more — orchestrated with live progress over WebSocket.",
  },
  {
    icon: Lock,
    title: "Enterprise Security",
    description: "CSRF protection, MFA, audit trails, and consent-gated authorized targets.",
  },
];

export function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background cyber-grid">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-cyan-500/5 via-transparent to-purple-500/5" />
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-cyan-500/10 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-purple-500/10 blur-3xl" />

      <header className="relative z-10 flex items-center justify-between px-6 py-6 lg:px-12">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-8 w-8 text-cyan-400" aria-hidden />
          <span className="text-xl font-bold tracking-tight">
            Compliance<span className="text-cyan-400">Guard</span>
          </span>
        </div>
        <nav className="flex items-center gap-3" aria-label="Landing navigation">
          <Link to="/login">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link to="/register">
            <Button variant="cyber">Get started</Button>
          </Link>
        </nav>
      </header>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-24 pt-16 text-center lg:px-12 lg:pt-24">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-1.5 text-sm text-cyan-300">
            <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" aria-hidden />
            AI-Powered Security & Compliance Platform
          </p>
          <h1 className="mx-auto max-w-4xl text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            <span className="text-gradient-cyber">Secure infrastructure.</span>
            <br />
            <span className="text-foreground">Prove compliance.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            ComplianceGuard orchestrates vulnerability scans, maps findings to regulatory
            frameworks, and delivers AI remediation — all with enterprise-grade audit trails.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link to="/register">
              <Button variant="cyber" size="lg" className="glow-cyan min-w-[200px]">
                Start free assessment
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="outline" size="lg" className="min-w-[200px]">
                View dashboard
              </Button>
            </Link>
          </div>
        </motion.div>

        <motion.div
          className="mx-auto mt-20 max-w-4xl rounded-xl border border-cyan-500/20 bg-card/40 p-1 glow-cyan backdrop-blur"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <div className="rounded-lg bg-background/80 p-6 font-mono text-left text-sm">
            <div className="flex gap-2 mb-4">
              <span className="h-3 w-3 rounded-full bg-red-500/80" />
              <span className="h-3 w-3 rounded-full bg-yellow-500/80" />
              <span className="h-3 w-3 rounded-full bg-green-500/80" />
            </div>
            <p className="text-cyan-400">$ complianceguard scan --target api.example.com</p>
            <p className="text-muted-foreground mt-2">→ Initializing scanners: nmap, nuclei, zap</p>
            <p className="text-emerald-400 mt-1">✓ Compliance score: 87% · 3 critical findings</p>
            <p className="text-purple-400 mt-1">✓ AI remediation generated for CVE-2024-XXXX</p>
          </div>
        </motion.div>
      </section>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-24 lg:px-12">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, description }, i) => (
            <motion.article
              key={title}
              className="rounded-xl border border-border/50 bg-card/40 p-6 backdrop-blur transition-colors hover:border-cyan-500/30"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.1 }}
            >
              <Icon className="h-8 w-8 text-cyan-400 mb-4" aria-hidden />
              <h2 className="font-semibold">{title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{description}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <footer className="relative z-10 border-t border-border/50 py-8 text-center text-sm text-muted-foreground">
        © {new Date().getFullYear()} ComplianceGuard. All rights reserved.
      </footer>
    </div>
  );
}
