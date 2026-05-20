import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, X, Loader2, Ban, Crosshair } from "lucide-react";
import { AddTargetDialog } from "@/components/targets/AddTargetDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { scansApi } from "@/api/scans";
import { useAuthStore } from "@/store/authStore";
import { useScanWebSocket } from "@/hooks/useScanWebSocket";
import { getApiErrorMessage } from "@/lib/api";
import { formatDate, SCAN_STATUS_LABELS } from "@/lib/utils";
import type { ScanType, ScannerType } from "@/types";

const createScanSchema = z.object({
  authorized_target_id: z.string().uuid("Select a target"),
  scan_type: z.enum([
    "infrastructure",
    "web_application",
    "api",
    "container",
    "full_assessment",
  ]),
  scanners_enabled: z.array(z.string()).min(1, "Select at least one scanner"),
  consent_confirmed: z.literal(true, {
    errorMap: () => ({ message: "You must confirm authorization to scan" }),
  }),
});

type CreateScanForm = z.infer<typeof createScanSchema>;

const SCAN_TYPES: { value: ScanType; label: string }[] = [
  { value: "infrastructure", label: "Infrastructure" },
  { value: "web_application", label: "Web Application" },
  { value: "api", label: "API" },
  { value: "container", label: "Container" },
  { value: "full_assessment", label: "Full Assessment" },
];

/** Backend scanner adapters currently available */
const SCANNERS: { value: ScannerType; label: string }[] = [
  { value: "nmap", label: "Nmap" },
  { value: "nuclei", label: "Nuclei" },
  { value: "zap", label: "OWASP ZAP" },
];

export function ScansPage() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuthStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [targetDialogOpen, setTargetDialogOpen] = useState(false);
  const [activeWsScanId, setActiveWsScanId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: () => scansApi.listScans({ page: 1, page_size: 50 }),
  });

  const {
    data: targets,
    isLoading: targetsLoading,
    isError: targetsError,
    refetch: refetchTargets,
  } = useQuery({
    queryKey: ["targets"],
    queryFn: scansApi.listTargets,
  });

  const { progress } = useScanWebSocket({
    scanId: activeWsScanId,
    token: accessToken,
    enabled: !!activeWsScanId && !!accessToken,
    onComplete: () => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      setActiveWsScanId(null);
    },
  });

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateScanForm>({
    resolver: zodResolver(createScanSchema),
    defaultValues: {
      scan_type: "infrastructure",
      scanners_enabled: ["nmap", "nuclei"],
      consent_confirmed: undefined,
    },
  });

  const selectedScanners = watch("scanners_enabled") ?? [];

  const createMutation = useMutation({
    mutationFn: scansApi.createScan,
    onSuccess: (scan) => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      setModalOpen(false);
      reset();
      setActiveWsScanId(scan.id);
    },
    onError: (err) => setFormError(getApiErrorMessage(err)),
  });

  const cancelMutation = useMutation({
    mutationFn: scansApi.cancelScan,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["scans"] }),
  });

  const toggleScanner = (scanner: string) => {
    const current = selectedScanners;
    const next = current.includes(scanner)
      ? current.filter((s) => s !== scanner)
      : [...current, scanner];
    setValue("scanners_enabled", next, { shouldValidate: true });
  };

  const onSubmit = (data: CreateScanForm) => {
    setFormError(null);
    createMutation.mutate({
      authorized_target_id: data.authorized_target_id,
      scan_type: data.scan_type,
      scanners_enabled: data.scanners_enabled as ScannerType[],
      consent_confirmed: true,
    });
  };

  const scans = scansData?.items ?? [];
  const liveProgress = progress;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Scans</h1>
          <p className="text-muted-foreground">Manage and monitor security assessments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setTargetDialogOpen(true)}>
            <Crosshair className="h-4 w-4" />
            Add target
          </Button>
          <Button
            variant="cyber"
            onClick={() => {
              refetchTargets();
              setModalOpen(true);
            }}
          >
            <Plus className="h-4 w-4" />
            New scan
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Authorized targets</CardTitle>
            <CardDescription>
              Targets must be registered before you can scan them
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => setTargetDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Add target
          </Button>
        </CardHeader>
        <CardContent>
          {targetsLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : targetsError ? (
            <p className="text-sm text-destructive">
              Could not load targets. Refresh the page or sign in again.
            </p>
          ) : !targets?.length ? (
            <div className="rounded-lg border border-dashed border-border/60 py-8 text-center">
              <p className="text-muted-foreground mb-4">No authorized targets yet.</p>
              <Button variant="cyber" onClick={() => setTargetDialogOpen(true)}>
                <Plus className="h-4 w-4" />
                Add your first target
              </Button>
              <p className="mt-4 text-xs text-muted-foreground max-w-md mx-auto">
                Use a public URL or domain you control (e.g. https://example.com). Localhost and
                private networks are not allowed.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border/40">
              {targets.map((t) => (
                <li key={t.id} className="flex items-center justify-between py-3 text-sm">
                  <span className="font-mono text-cyan-300/90">{t.normalized_target}</span>
                  <Badge variant="secondary">{t.target_type}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {liveProgress && (
        <Card className="border-cyan-500/30 bg-cyan-500/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium">Live scan progress</p>
                <p className="text-xs text-muted-foreground">
                  {liveProgress.current_phase ?? liveProgress.status} — {liveProgress.progress_percent}%
                </p>
              </div>
              <div className="h-2 flex-1 max-w-xs rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-cyan-500 transition-all duration-500"
                  style={{ width: `${liveProgress.progress_percent}%` }}
                  role="progressbar"
                  aria-valuenow={liveProgress.progress_percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Scan history</CardTitle>
          <CardDescription>{scansData?.total ?? 0} total scans</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : scans.length === 0 ? (
            <p className="py-12 text-center text-muted-foreground">No scans found. Create one to get started.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-left text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">Target</th>
                    <th className="pb-3 pr-4 font-medium">Type</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 pr-4 font-medium">Progress</th>
                    <th className="pb-3 pr-4 font-medium">Created</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((scan) => (
                    <tr key={scan.id} className="border-b border-border/30">
                      <td className="py-3 pr-4 font-mono text-xs max-w-[200px] truncate">{scan.target_value}</td>
                      <td className="py-3 pr-4 capitalize">{scan.scan_type.replace(/_/g, " ")}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={scan.status === "completed" ? "success" : scan.status === "failed" ? "critical" : "secondary"}>
                          {SCAN_STATUS_LABELS[scan.status] ?? scan.status}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">{scan.progress_percent}%</td>
                      <td className="py-3 pr-4 text-muted-foreground">{formatDate(scan.created_at)}</td>
                      <td className="py-3">
                        {["running", "queued", "pending", "validating"].includes(scan.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => cancelMutation.mutate(scan.id)}
                            disabled={cancelMutation.isPending}
                            aria-label={`Cancel scan ${scan.id}`}
                          >
                            <Ban className="h-4 w-4" />
                          </Button>
                        )}
                        {["running", "queued"].includes(scan.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setActiveWsScanId(scan.id)}
                            className="text-cyan-400"
                          >
                            Watch
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <AnimatePresence>
        {modalOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-50 bg-black/70"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setModalOpen(false)}
              aria-hidden
            />
            <motion.div
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="create-scan-title"
            >
              <Card
                className="w-full max-w-lg max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <CardHeader className="flex flex-row items-start justify-between">
                  <div>
                    <CardTitle id="create-scan-title">Create new scan</CardTitle>
                    <CardDescription>Configure scanners and confirm authorization</CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setModalOpen(false)} aria-label="Close">
                    <X className="h-4 w-4" />
                  </Button>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    {formError && (
                      <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
                        {formError}
                      </div>
                    )}
                    <div>
                      <label htmlFor="target" className="mb-1.5 block text-sm font-medium">
                        Authorized target
                      </label>
                      <select
                        id="target"
                        className="flex h-10 w-full rounded-md border border-input bg-background/50 px-3 text-sm"
                        {...register("authorized_target_id")}
                      >
                        <option value="">Select target…</option>
                        {(targets ?? []).map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.normalized_target} ({t.target_type})
                          </option>
                        ))}
                      </select>
                      {errors.authorized_target_id && (
                        <p className="mt-1 text-xs text-destructive">{errors.authorized_target_id.message}</p>
                      )}
                      {!targets?.length && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          No targets yet.{" "}
                          <button
                            type="button"
                            className="text-cyan-400 hover:underline"
                            onClick={() => {
                              setModalOpen(false);
                              setTargetDialogOpen(true);
                            }}
                          >
                            Add an authorized target
                          </button>{" "}
                          first.
                        </p>
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="mt-2 h-8 text-cyan-400"
                        onClick={() => {
                          setModalOpen(false);
                          setTargetDialogOpen(true);
                        }}
                      >
                        <Plus className="h-3 w-3" />
                        Add new target
                      </Button>
                    </div>
                    <div>
                      <label htmlFor="scan_type" className="mb-1.5 block text-sm font-medium">
                        Scan type
                      </label>
                      <select
                        id="scan_type"
                        className="flex h-10 w-full rounded-md border border-input bg-background/50 px-3 text-sm"
                        {...register("scan_type")}
                      >
                        {SCAN_TYPES.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <span className="mb-2 block text-sm font-medium">Scanners</span>
                      <div className="flex flex-wrap gap-2">
                        {SCANNERS.map((s) => (
                          <button
                            key={s.value}
                            type="button"
                            onClick={() => toggleScanner(s.value)}
                            className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                              selectedScanners.includes(s.value)
                                ? "border-cyan-500/50 bg-cyan-500/15 text-cyan-300"
                                : "border-border bg-transparent text-muted-foreground hover:border-border/80"
                            }`}
                          >
                            {s.label}
                          </button>
                        ))}
                      </div>
                      {errors.scanners_enabled && (
                        <p className="mt-1 text-xs text-destructive">{errors.scanners_enabled.message}</p>
                      )}
                    </div>
                    <label className="flex items-start gap-3 rounded-lg border border-border/50 p-4 cursor-pointer">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4 rounded border-input"
                        {...register("consent_confirmed")}
                      />
                      <span className="text-sm">
                        I confirm that I have explicit authorization to scan the selected target(s) and
                        accept responsibility for this assessment under my organization&apos;s security policy.
                      </span>
                    </label>
                    {errors.consent_confirmed && (
                      <p className="text-xs text-destructive">{errors.consent_confirmed.message}</p>
                    )}
                    <div className="flex gap-3 pt-2">
                      <Button type="button" variant="outline" className="flex-1" onClick={() => setModalOpen(false)}>
                        Cancel
                      </Button>
                      <Button type="submit" variant="cyber" className="flex-1" disabled={isSubmitting}>
                        {isSubmitting ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Starting…
                          </>
                        ) : (
                          "Start scan"
                        )}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <AddTargetDialog
        open={targetDialogOpen}
        onClose={() => setTargetDialogOpen(false)}
        onCreated={(targetId) => {
          setValue("authorized_target_id", targetId);
          refetchTargets();
          setModalOpen(true);
        }}
      />
    </div>
  );
}
