import { useState, useMemo, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, Filter, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FindingResolutionDialog } from "@/components/findings/FindingResolutionDialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";import { Input } from "@/components/ui/input";
import { Badge, severityBadgeVariant } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { scansApi } from "@/api/scans";
import { formatDate } from "@/lib/utils";
import type { Finding, Severity } from "@/types";

const SEVERITIES: (Severity | "all")[] = ["all", "critical", "high", "medium", "low", "info"];

export function FindingsPage() {
  const [searchParams] = useSearchParams();
  const scanFromUrl = searchParams.get("scan");
  const [selectedScanId, setSelectedScanId] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all");
  const [search, setSearch] = useState("");
  const [guideFinding, setGuideFinding] = useState<Finding | null>(null);

  useEffect(() => {
    if (scanFromUrl) {
      setSelectedScanId(scanFromUrl);
    }
  }, [scanFromUrl]);

  const { data: scansData, isLoading: scansLoading } = useQuery({
    queryKey: ["scans-for-findings"],
    queryFn: () => scansApi.listScans({ page: 1, page_size: 50, status: "completed" }),
  });

  const completedScans = scansData?.items ?? [];

  const effectiveScanId = selectedScanId || completedScans[0]?.id || "";

  const { data: findings, isLoading: findingsLoading } = useQuery({
    queryKey: ["findings", effectiveScanId, severityFilter],
    queryFn: () =>
      scansApi.getFindings(
        effectiveScanId,
        severityFilter === "all" ? undefined : severityFilter
      ),
    enabled: !!effectiveScanId,
  });

  const filteredFindings = useMemo(() => {
    if (!findings) return [];
    const q = search.toLowerCase().trim();
    if (!q) return findings;
    return findings.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q) ||
        f.affected_asset.toLowerCase().includes(q) ||
        (f.cve_id?.toLowerCase().includes(q) ?? false)
    );
  }, [findings, search]);

  const isLoading = scansLoading || findingsLoading;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Findings</h1>
        <p className="text-muted-foreground">
          Vulnerabilities from scans — use <strong className="text-purple-400 font-medium">Fix guide</strong> for
          step-by-step AI remediation help.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" aria-hidden />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="scan-select" className="mb-1.5 block text-sm font-medium">
              Scan
            </label>
            <select
              id="scan-select"
              className="flex h-10 w-full rounded-md border border-input bg-background/50 px-3 text-sm"
              value={effectiveScanId}
              onChange={(e) => setSelectedScanId(e.target.value)}
            >
              {completedScans.length === 0 ? (
                <option value="">No completed scans</option>
              ) : (
                completedScans.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.target_value} — {formatDate(s.completed_at)}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="severity-filter" className="mb-1.5 block text-sm font-medium">
              Severity
            </label>
            <select
              id="severity-filter"
              className="flex h-10 w-full rounded-md border border-input bg-background/50 px-3 text-sm"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as Severity | "all")}
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s === "all" ? "All severities" : s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[240px]">
            <label htmlFor="search" className="mb-1.5 block text-sm font-medium">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <Input
                id="search"
                placeholder="Title, CVE, asset…"
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Findings table</CardTitle>
          <CardDescription>
            {filteredFindings.length} finding{filteredFindings.length !== 1 ? "s" : ""} displayed
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : !effectiveScanId ? (
            <p className="py-12 text-center text-muted-foreground">
              Complete a scan to view findings.
            </p>
          ) : filteredFindings.length === 0 ? (
            <p className="py-12 text-center text-muted-foreground">No findings match your filters.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-left text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">Severity</th>
                    <th className="pb-3 pr-4 font-medium">Title</th>
                    <th className="pb-3 pr-4 font-medium">Scanner</th>
                    <th className="pb-3 pr-4 font-medium">Asset</th>
                    <th className="pb-3 pr-4 font-medium">CVSS</th>
                    <th className="pb-3 pr-4 font-medium">CVE</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFindings.map((finding: Finding) => (
                    <tr key={finding.id} className="border-b border-border/30 align-top">
                      <td className="py-4 pr-4">
                        <Badge variant={severityBadgeVariant(finding.severity)}>
                          {finding.severity}
                        </Badge>
                      </td>
                      <td className="py-4 pr-4 max-w-xs">
                        <p className="font-medium">{finding.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                          {finding.description}
                        </p>
                        {finding.ai_remediation && (
                          <p className="mt-2 text-xs text-purple-400 border-l-2 border-purple-500/40 pl-2">
                            AI: {finding.ai_remediation.slice(0, 120)}
                            {finding.ai_remediation.length > 120 ? "…" : ""}
                          </p>
                        )}
                      </td>
                      <td className="py-4 pr-4 font-mono text-xs">{finding.scanner}</td>
                      <td className="py-4 pr-4 font-mono text-xs max-w-[140px] truncate">
                        {finding.affected_asset}
                      </td>
                      <td className="py-4 pr-4">{finding.cvss_score?.toFixed(1) ?? "—"}</td>
                      <td className="py-4 pr-4 font-mono text-xs">{finding.cve_id ?? "—"}</td>
                      <td className="py-4">
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-purple-300 border-purple-500/40 hover:bg-purple-500/10"
                          onClick={() => setGuideFinding(finding)}
                          disabled={!effectiveScanId}
                        >
                          <Sparkles className="h-3.5 w-3.5" />
                          Fix guide
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <FindingResolutionDialog
        finding={guideFinding}
        scanId={effectiveScanId}
        open={!!guideFinding}
        onClose={() => setGuideFinding(null)}
      />
    </div>
  );
}
