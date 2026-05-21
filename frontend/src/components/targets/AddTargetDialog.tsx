import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingOverlay } from "@/components/ui/loading-overlay";
import { scansApi } from "@/api/scans";
import { getApiErrorMessage } from "@/lib/api";

const targetSchema = z.object({
  target_value: z.string().min(3, "Enter a URL, domain, or IP"),
  target_type: z.enum(["url", "domain", "ip", "cidr"]),
  verification_method: z.string().min(3, "Describe how ownership was verified"),
  ownership_proof: z.string().optional(),
  notes: z.string().optional(),
  consent_confirmed: z.literal(true, {
    errorMap: () => ({ message: "You must confirm authorization to scan this target" }),
  }),
});

type TargetForm = z.infer<typeof targetSchema>;

interface AddTargetDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (targetId: string) => void;
}

export function AddTargetDialog({ open, onClose, onCreated }: AddTargetDialogProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TargetForm>({
    resolver: zodResolver(targetSchema),
    defaultValues: {
      target_type: "url",
      verification_method: "dns_txt_record",
      consent_confirmed: undefined,
    },
  });

  const mutation = useMutation({
    mutationFn: scansApi.createTarget,
    onSuccess: (target) => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      reset();
      setError(null);
      onCreated?.(target.id);
      onClose();
    },
    onError: (err) => setError(getApiErrorMessage(err)),
  });

  const isSaving = mutation.isPending;

  const handleClose = () => {
    if (isSaving) return;
    onClose();
  };

  const onSubmit = (data: TargetForm) => {
    if (isSaving) return;
    setError(null);
    mutation.mutate({
      target_value: data.target_value,
      target_type: data.target_type,
      verification_method: data.verification_method,
      ownership_proof: data.ownership_proof,
      notes: data.notes,
      consent_confirmed: true,
    });
  };

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-[60] bg-black/70"
        onClick={handleClose}
        aria-hidden
      />
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-target-title"
        aria-busy={isSaving}
      >
        <Card
          className="relative w-full max-w-md overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          <LoadingOverlay show={isSaving} label="Adding target…" />
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle id="add-target-title">Add authorized target</CardTitle>
              <CardDescription>
                Register a target you own before running scans. Localhost and private IPs are blocked.
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleClose}
              disabled={isSaving}
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {error && (
                <div
                  className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                  role="alert"
                >
                  {error}
                </div>
              )}
              <div>
                <label htmlFor="target_value" className="mb-1.5 block text-sm font-medium">
                  Target
                </label>
                <Input
                  id="target_value"
                  placeholder="https://example.com or api.example.com"
                  disabled={isSaving}
                  {...register("target_value")}
                  error={errors.target_value?.message}
                />
              </div>
              <div>
                <label htmlFor="target_type" className="mb-1.5 block text-sm font-medium">
                  Type
                </label>
                <select
                  id="target_type"
                  className="flex h-10 w-full rounded-md border border-input bg-background/50 px-3 text-sm disabled:opacity-50"
                  disabled={isSaving}
                  {...register("target_type")}
                >
                  <option value="url">URL</option>
                  <option value="domain">Domain</option>
                  <option value="ip">IP address</option>
                  <option value="cidr">CIDR range</option>
                </select>
              </div>
              <div>
                <label htmlFor="verification_method" className="mb-1.5 block text-sm font-medium">
                  Verification method
                </label>
                <select
                  id="verification_method"
                  className="flex h-10 w-full rounded-md border border-input bg-background/50 px-3 text-sm disabled:opacity-50"
                  disabled={isSaving}
                  {...register("verification_method")}
                >
                  <option value="dns_txt_record">DNS TXT record</option>
                  <option value="email_verification">Email verification</option>
                  <option value="contract_scope">Contract / scope document</option>
                  <option value="internal_inventory">Internal asset inventory</option>
                </select>
              </div>
              <div>
                <label htmlFor="ownership_proof" className="mb-1.5 block text-sm font-medium">
                  Ownership proof (optional)
                </label>
                <Input
                  id="ownership_proof"
                  placeholder="e.g. TXT record value, ticket ID"
                  disabled={isSaving}
                  {...register("ownership_proof")}
                />
              </div>
              <label className="flex items-start gap-3 rounded-lg border border-border/50 p-4 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-input disabled:opacity-50"
                  disabled={isSaving}
                  {...register("consent_confirmed")}
                />
                <span className="text-sm">
                  I confirm I am authorized to assess this target and have documented ownership verification.
                </span>
              </label>
              {errors.consent_confirmed && (
                <p className="text-xs text-destructive">{errors.consent_confirmed.message}</p>
              )}
              <div className="flex gap-3 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1"
                  onClick={handleClose}
                  disabled={isSaving}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="cyber" className="flex-1" disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Saving…
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4" />
                      Add target
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
