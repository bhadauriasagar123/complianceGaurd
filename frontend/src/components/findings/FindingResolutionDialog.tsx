import { useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Sparkles, X, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingOverlay } from "@/components/ui/loading-overlay";
import { scansApi } from "@/api/scans";
import { getApiErrorMessage } from "@/lib/api";
import type { Finding, FindingResolutionGuide } from "@/types";

interface FindingResolutionDialogProps {
  finding: Finding | null;
  scanId: string;
  open: boolean;
  onClose: () => void;
}

export function FindingResolutionDialog({
  finding,
  scanId,
  open,
  onClose,
}: FindingResolutionDialogProps) {
  const mutation = useMutation({
    mutationFn: () => scansApi.getResolutionGuide(scanId, finding!.id),
  });

  const isLoading = mutation.isPending;
  const guide: FindingResolutionGuide | undefined = mutation.data;

  useEffect(() => {
    if (open && finding && mutation.status === "idle") {
      mutation.mutate();
    }
  }, [open, finding?.id, scanId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) {
      mutation.reset();
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!open || !finding) return null;

  const handleClose = () => {
    if (isLoading) return;
    mutation.reset();
    onClose();
  };

  return (
    <>
      <div className="fixed inset-0 z-[70] bg-black/70" onClick={handleClose} aria-hidden />
      <div
        className="fixed inset-0 z-[70] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="resolution-guide-title"
        aria-busy={isLoading}
      >
        <Card
          className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <LoadingOverlay show={isLoading} label="Generating resolution guide…" />
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-400" aria-hidden />
                <CardTitle id="resolution-guide-title">AI resolution guide</CardTitle>
                {guide && (
                  <Badge variant={guide.powered_by_ai ? "secondary" : "outline"}>
                    {guide.powered_by_ai
                      ? guide.ai_provider === "openai"
                        ? "OpenAI powered"
                        : guide.ai_provider === "anthropic"
                          ? "Claude powered"
                          : "AI powered"
                      : "Expert playbook"}
                  </Badge>
                )}
              </div>
              <CardDescription className="font-medium text-foreground">{finding.title}</CardDescription>
              <p className="text-xs text-muted-foreground font-mono">{finding.affected_asset}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={handleClose} disabled={isLoading} aria-label="Close">
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-6">
            {mutation.isError && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {getApiErrorMessage(mutation.error)}
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => mutation.mutate()}
                  disabled={isLoading}
                >
                  Retry
                </Button>
              </div>
            )}

            {guide && (
              <>
                <div className="rounded-lg border border-purple-500/30 bg-purple-500/5 p-4">
                  <p className="text-sm leading-relaxed">{guide.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                    <span>
                      Priority: <strong className="text-foreground capitalize">{guide.priority}</strong>
                    </span>
                    <span>
                      Effort: <strong className="text-foreground">{guide.estimated_effort}</strong>
                    </span>
                    <span>
                      Confidence: <strong className="text-foreground">{Math.round(guide.confidence * 100)}%</strong>
                    </span>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold mb-3">Step-by-step fix</h3>
                  <ol className="space-y-4">
                    {guide.steps
                      .slice()
                      .sort((a, b) => a.order - b.order)
                      .map((step) => (
                        <li
                          key={step.order}
                          className="rounded-lg border border-border/50 bg-card/50 p-4"
                        >
                          <div className="flex gap-3">
                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-300">
                              {step.order}
                            </span>
                            <div className="space-y-2 min-w-0">
                              <p className="font-medium text-sm">{step.title}</p>
                              <p className="text-sm text-muted-foreground">{step.description}</p>
                              <p className="flex items-start gap-2 text-xs text-emerald-400/90">
                                <CheckCircle2 className="h-3.5 w-3.5 shrink-0 mt-0.5" aria-hidden />
                                <span>
                                  <strong className="text-emerald-400">Verify:</strong> {step.verification}
                                </span>
                              </p>
                            </div>
                          </div>
                        </li>
                      ))}
                  </ol>
                </div>

                {guide.compliance_notes && (
                  <div className="rounded-lg border border-border/40 p-4 text-sm text-muted-foreground">
                    <p className="font-medium text-foreground mb-1">Compliance note</p>
                    {guide.compliance_notes}
                  </div>
                )}
              </>
            )}

            {!guide && !mutation.isError && isLoading && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Analyzing finding and building your fix plan…
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={handleClose} disabled={isLoading}>
                Close
              </Button>
              {guide && (
                <Button
                  variant="cyber"
                  disabled={isLoading}
                  onClick={() => mutation.mutate()}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Refreshing…
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      Regenerate guide
                    </>
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
