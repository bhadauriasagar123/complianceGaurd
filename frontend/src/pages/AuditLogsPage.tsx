import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ScrollText } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { auditApi } from "@/api/audit";
import { formatDate } from "@/lib/utils";

const ACTION_OPTIONS = [
  { value: "", label: "All actions" },
  { value: "login", label: "Login" },
  { value: "logout", label: "Logout" },
  { value: "scan_created", label: "Scan created" },
  { value: "scan_completed", label: "Scan completed" },
  { value: "target_authorized", label: "Target authorized" },
  { value: "mfa_enabled", label: "MFA enabled" },
];

export function AuditLogsPage() {
  const [actionFilter, setActionFilter] = useState("");

  const { data: logs, isLoading } = useQuery({
    queryKey: ["audit-logs", actionFilter],
    queryFn: () =>
      auditApi.listLogs({
        page: 1,
        page_size: 100,
        action: actionFilter || undefined,
      }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <ScrollText className="h-7 w-7 text-cyan-400" aria-hidden />
          Audit logs
        </h1>
        <p className="text-muted-foreground">Immutable activity trail for your organization</p>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Activity log</CardTitle>
            <CardDescription>{logs?.length ?? 0} entries loaded</CardDescription>
          </div>
          <div className="w-full sm:w-56">
            <label htmlFor="action-filter" className="sr-only">
              Filter by action
            </label>
            <select
              id="action-filter"
              className="flex h-10 w-full rounded-md border border-input bg-background/50 px-3 text-sm"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            >
              {ACTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !logs?.length ? (
            <p className="py-12 text-center text-muted-foreground">No audit logs found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-left text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">Action</th>
                    <th className="pb-3 pr-4 font-medium">Outcome</th>
                    <th className="pb-3 pr-4 font-medium">Resource</th>
                    <th className="pb-3 pr-4 font-medium">Message</th>
                    <th className="pb-3 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-border/30">
                      <td className="py-3 pr-4">
                        <Badge variant="outline" className="font-mono text-xs">
                          {log.action}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={log.outcome === "success" ? "success" : "critical"}>
                          {log.outcome}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">
                        {log.resource_type ?? "—"}
                        {log.resource_id ? ` / ${log.resource_id.slice(0, 8)}…` : ""}
                      </td>
                      <td className="py-3 pr-4 max-w-md truncate text-muted-foreground">
                        {log.message ?? "—"}
                      </td>
                      <td className="py-3 text-muted-foreground whitespace-nowrap">
                        {formatDate(log.created_at)}
                      </td>
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
