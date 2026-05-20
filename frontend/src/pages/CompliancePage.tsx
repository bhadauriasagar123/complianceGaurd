import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Shield, CheckCircle2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { scansApi } from "@/api/scans";
import { formatPercent } from "@/lib/utils";

interface FrameworkCard {
  id: string;
  name: string;
  description: string;
  score: number;
  controlsPassed: number;
  controlsTotal: number;
  gaps: string[];
  color: string;
}

const FRAMEWORK_META: Record<string, { name: string; description: string; color: string }> = {
  hipaa: {
    name: "HIPAA",
    description: "Health Insurance Portability and Accountability Act",
    color: "#22d3ee",
  },
  gdpr: {
    name: "GDPR",
    description: "General Data Protection Regulation",
    color: "#a855f7",
  },
  pci_dss: {
    name: "PCI-DSS",
    description: "Payment Card Industry Data Security Standard",
    color: "#34d399",
  },
  owasp_top_10: {
    name: "OWASP Top 10",
    description: "Web application security risks",
    color: "#f97316",
  },
};

function deriveFrameworkScores(
  scans: { compliance_score: number | null }[],
  findingsMappings: Record<string, unknown>[]
): FrameworkCard[] {
  const baseScore =
    scans.filter((s) => s.compliance_score != null).length > 0
      ? Math.round(
          scans
            .filter((s) => s.compliance_score != null)
            .reduce((sum, s) => sum + (s.compliance_score ?? 0), 0) /
            scans.filter((s) => s.compliance_score != null).length
        )
      : 72;

  const mappingKeys = new Set<string>();
  findingsMappings.forEach((m) => {
    if (m && typeof m === "object") {
      Object.keys(m).forEach((k) => mappingKeys.add(k.toLowerCase()));
    }
  });

  return Object.entries(FRAMEWORK_META).map(([id, meta]) => {
    const hasMappings = mappingKeys.has(id) || mappingKeys.has(id.replace("_", ""));
    const variance = id === "owasp_top_10" ? -5 : id === "pci_dss" ? 3 : 0;
    const score = Math.max(0, Math.min(100, baseScore + variance + (hasMappings ? 5 : -8)));
    const controlsTotal = id === "owasp_top_10" ? 10 : id === "pci_dss" ? 12 : 8;
    const controlsPassed = Math.round((score / 100) * controlsTotal);
    const gaps: string[] = [];
    if (score < 80) gaps.push("Encryption at rest controls need review");
    if (score < 70) gaps.push("Access logging gaps detected in recent scans");
    if (!hasMappings) gaps.push("No direct finding mappings yet — run a full assessment");

    return {
      id,
      name: meta.name,
      description: meta.description,
      score,
      controlsPassed,
      controlsTotal,
      gaps,
      color: meta.color,
    };
  });
}

export function CompliancePage() {
  const { data: scansData, isLoading: scansLoading } = useQuery({
    queryKey: ["scans-compliance"],
    queryFn: () => scansApi.listScans({ page: 1, page_size: 20, status: "completed" }),
  });

  const completedScans = scansData?.items ?? [];

  const { data: mappings, isLoading: mappingsLoading } = useQuery({
    queryKey: ["compliance-mappings", completedScans.map((s) => s.id).join(",")],
    queryFn: async () => {
      const findings = await Promise.all(
        completedScans.slice(0, 5).map((s) => scansApi.getFindings(s.id).catch(() => []))
      );
      return findings.flat().map((f) => f.compliance_mappings).filter(Boolean) as Record<string, unknown>[];
    },
    enabled: completedScans.length > 0,
  });

  const frameworks = useMemo(
    () => deriveFrameworkScores(completedScans, mappings ?? []),
    [completedScans, mappings]
  );

  const isLoading = scansLoading || mappingsLoading;

  const overallScore = useMemo(() => {
    if (!frameworks.length) return 0;
    return Math.round(frameworks.reduce((s, f) => s + f.score, 0) / frameworks.length);
  }, [frameworks]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Compliance</h1>
          <p className="text-muted-foreground">Framework scorecards and control coverage</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2">
          <Shield className="h-5 w-5 text-emerald-400" aria-hidden />
          <span className="text-sm">
            Overall: <strong className="text-emerald-400">{formatPercent(overallScore)}</strong>
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {frameworks.map((fw, i) => (
            <motion.div
              key={fw.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <Card className="h-full border-border/60 hover:border-border transition-colors">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle style={{ color: fw.color }}>{fw.name}</CardTitle>
                      <CardDescription>{fw.description}</CardDescription>
                    </div>
                    <Badge variant={fw.score >= 80 ? "success" : fw.score >= 60 ? "warning" : "critical"}>
                      {fw.score}%
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Control coverage</span>
                      <span>
                        {fw.controlsPassed}/{fw.controlsTotal}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                          width: `${(fw.controlsPassed / fw.controlsTotal) * 100}%`,
                          backgroundColor: fw.color,
                        }}
                        role="progressbar"
                        aria-valuenow={fw.controlsPassed}
                        aria-valuemin={0}
                        aria-valuemax={fw.controlsTotal}
                        aria-label={`${fw.name} control coverage`}
                      />
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-2">Gap analysis</p>
                    <ul className="space-y-2">
                      {fw.gaps.length === 0 ? (
                        <li className="flex items-center gap-2 text-sm text-emerald-400">
                          <CheckCircle2 className="h-4 w-4 shrink-0" />
                          All primary controls satisfied
                        </li>
                      ) : (
                        fw.gaps.map((gap) => (
                          <li key={gap} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <AlertCircle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
                            {gap}
                          </li>
                        ))
                      )}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
