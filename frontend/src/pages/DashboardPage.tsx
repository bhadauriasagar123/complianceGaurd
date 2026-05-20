import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Activity, AlertTriangle, Shield, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { scansApi } from "@/api/scans";
import { formatPercent, SEVERITY_COLORS, SCAN_STATUS_LABELS } from "@/lib/utils";

const FRAMEWORKS = [
  { id: "hipaa", label: "HIPAA", color: "#22d3ee" },
  { id: "gdpr", label: "GDPR", color: "#a855f7" },
  { id: "pci_dss", label: "PCI-DSS", color: "#34d399" },
  { id: "owasp_top_10", label: "OWASP", color: "#f97316" },
];

function ComplianceRing({ score, label, color }: { score: number; label: string; color: string }) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="88" height="88" className="-rotate-90" aria-hidden>
        <circle cx="44" cy="44" r={radius} fill="none" stroke="currentColor" strokeOpacity={0.1} strokeWidth="8" />
        <circle
          cx="44"
          cy="44"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <span className="text-lg font-bold" style={{ color }}>{score}%</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function DashboardPage() {
  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans", { page: 1, page_size: 10 }],
    queryFn: () => scansApi.listScans({ page: 1, page_size: 10 }),
  });

  const recentScans = scansData?.items ?? [];

  const severityData = useMemo(() => {
    const counts: Record<string, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    };
    return Object.entries(counts).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
      fill: SEVERITY_COLORS[name],
    }));
  }, []);

  const { data: findingsAgg } = useQuery({
    queryKey: ["dashboard-findings", recentScans.map((s) => s.id).join(",")],
    queryFn: async () => {
      const completed = recentScans.filter((s) => s.status === "completed").slice(0, 5);
      const allFindings = await Promise.all(
        completed.map((s) => scansApi.getFindings(s.id).catch(() => []))
      );
      const counts: Record<string, number> = {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        info: 0,
      };
      allFindings.flat().forEach((f) => {
        if (counts[f.severity] !== undefined) counts[f.severity]++;
      });
      return counts;
    },
    enabled: recentScans.length > 0,
  });

  const chartData = useMemo(() => {
    if (!findingsAgg) return severityData;
    return Object.entries(findingsAgg).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
      fill: SEVERITY_COLORS[name],
    }));
  }, [findingsAgg, severityData]);

  const avgCompliance = useMemo(() => {
    const scored = recentScans.filter((s) => s.compliance_score != null);
    if (!scored.length) return 0;
    return Math.round(
      scored.reduce((sum, s) => sum + (s.compliance_score ?? 0), 0) / scored.length
    );
  }, [recentScans]);

  const frameworkScores = useMemo(() => {
    const offsets: Record<string, number> = {
      hipaa: 2,
      gdpr: -3,
      pci_dss: 5,
      owasp_top_10: -6,
    };
    return FRAMEWORKS.map((fw) => ({
      ...fw,
      score: Math.max(0, Math.min(100, avgCompliance + (offsets[fw.id] ?? 0))),
    }));
  }, [avgCompliance]);

  const activeScans = recentScans.filter((s) =>
    ["running", "queued", "validating", "ai_processing", "normalizing"].includes(s.status)
  ).length;

  const criticalCount = findingsAgg?.critical ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Security posture and compliance overview</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Active scans", value: activeScans, icon: Activity, color: "text-cyan-400" },
          { label: "Critical findings", value: criticalCount, icon: AlertTriangle, color: "text-red-400" },
          { label: "Avg compliance", value: formatPercent(avgCompliance), icon: Shield, color: "text-emerald-400" },
          { label: "Total scans", value: scansData?.total ?? 0, icon: TrendingUp, color: "text-purple-400" },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card>
              <CardContent className="flex items-center gap-4 p-6">
                <stat.icon className={`h-8 w-8 ${stat.color}`} aria-hidden />
                <div>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Findings by severity</CardTitle>
            <CardDescription>Distribution from recent completed scans</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 18%)" />
                  <XAxis dataKey="name" tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} />
                  <YAxis tick={{ fill: "hsl(215 20% 55%)", fontSize: 12 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(222 47% 8%)",
                      border: "1px solid hsl(217 33% 18%)",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Compliance frameworks</CardTitle>
            <CardDescription>Estimated scores from scan compliance mappings</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
              {frameworkScores.map((fw) => (
                <ComplianceRing key={fw.id} score={fw.score} label={fw.label} color={fw.color} />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent scans</CardTitle>
            <CardDescription>Latest security assessments</CardDescription>
          </div>
          <Link to="/scans" className="text-sm text-cyan-400 hover:underline">
            View all
          </Link>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : recentScans.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No scans yet.{" "}
              <Link to="/scans" className="text-cyan-400 hover:underline">
                Create your first scan
              </Link>
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-left text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">Target</th>
                    <th className="pb-3 pr-4 font-medium">Type</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 pr-4 font-medium">Progress</th>
                    <th className="pb-3 font-medium">Compliance</th>
                  </tr>
                </thead>
                <tbody>
                  {recentScans.map((scan) => (
                    <tr key={scan.id} className="border-b border-border/30">
                      <td className="py-3 pr-4 font-mono text-xs">{scan.target_value}</td>
                      <td className="py-3 pr-4 capitalize">{scan.scan_type.replace(/_/g, " ")}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={scan.status === "completed" ? "success" : scan.status === "failed" ? "critical" : "secondary"}>
                          {SCAN_STATUS_LABELS[scan.status] ?? scan.status}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">{scan.progress_percent}%</td>
                      <td className="py-3">{formatPercent(scan.compliance_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
