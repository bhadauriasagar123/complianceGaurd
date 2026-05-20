import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, KeyRound, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
import { getApiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";

const mfaSchema = z.object({
  code: z.string().length(6, "Enter the 6-digit code from your authenticator"),
});

type MfaForm = z.infer<typeof mfaSchema>;

export function SettingsPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [mfaSetup, setMfaSetup] = useState<{
    secret: string;
    provisioning_uri: string;
    qr_code_base64: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<MfaForm>({
    resolver: zodResolver(mfaSchema),
  });

  const setupMutation = useMutation({
    mutationFn: authApi.setupMfa,
    onSuccess: (data) => {
      setMfaSetup(data);
      setError(null);
    },
    onError: (err) => setError(getApiErrorMessage(err)),
  });

  const enableMutation = useMutation({
    mutationFn: (code: string) => authApi.enableMfa(code),
    onSuccess: async () => {
      setSuccess("MFA enabled successfully");
      setMfaSetup(null);
      reset();
      await queryClient.invalidateQueries();
      const me = await authApi.getMe();
      useAuthStore.getState().setUser(me);
    },
    onError: (err) => setError(getApiErrorMessage(err)),
  });

  const onEnableMfa = (data: MfaForm) => {
    setError(null);
    setSuccess(null);
    enableMutation.mutate(data.code);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Account security and preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-cyan-400" aria-hidden />
            Profile
          </CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-sm text-muted-foreground">Name</p>
              <p className="font-medium">{user?.full_name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Email</p>
              <p className="font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Role</p>
              <p className="font-medium capitalize">{user?.role?.replace(/_/g, " ")}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Member since</p>
              <p className="font-medium">{formatDate(user?.created_at)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={user?.is_verified ? "success" : "warning"}>
              {user?.is_verified ? "Email verified" : "Email pending"}
            </Badge>
            <Badge variant={user?.mfa_enabled ? "success" : "secondary"}>
              MFA {user?.mfa_enabled ? "enabled" : "disabled"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-purple-400" aria-hidden />
            Multi-factor authentication
          </CardTitle>
          <CardDescription>
            Add an extra layer of security with TOTP authenticator apps
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
              {error}
            </div>
          )}
          {success && (
            <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400" role="status">
              {success}
            </div>
          )}

          {!user?.mfa_enabled && !mfaSetup && (
            <Button
              variant="outline"
              onClick={() => setupMutation.mutate()}
              disabled={setupMutation.isPending}
            >
              {setupMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Setting up…
                </>
              ) : (
                "Set up MFA"
              )}
            </Button>
          )}

          {mfaSetup && (
            <div className="space-y-4">
              <div className="flex justify-center rounded-lg border border-border/50 bg-background/50 p-4">
                <img
                  src={`data:image/png;base64,${mfaSetup.qr_code_base64}`}
                  alt="MFA QR code for authenticator app"
                  className="h-48 w-48"
                />
              </div>
              <p className="text-xs text-muted-foreground font-mono break-all">
                Secret: {mfaSetup.secret}
              </p>
              <form onSubmit={handleSubmit(onEnableMfa)} className="space-y-4">
                <div>
                  <label htmlFor="mfa-code" className="mb-1.5 block text-sm font-medium">
                    Verification code
                  </label>
                  <Input
                    id="mfa-code"
                    inputMode="numeric"
                    maxLength={6}
                    autoComplete="one-time-code"
                    {...register("code")}
                    error={errors.code?.message}
                  />
                </div>
                <Button type="submit" variant="cyber" disabled={isSubmitting || enableMutation.isPending}>
                  {(isSubmitting || enableMutation.isPending) ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Enabling…
                    </>
                  ) : (
                    "Enable MFA"
                  )}
                </Button>
              </form>
            </div>
          )}

          {user?.mfa_enabled && (
            <p className="text-sm text-emerald-400">Multi-factor authentication is active on your account.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API configuration</CardTitle>
          <CardDescription>Environment settings (read-only)</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-2 text-sm">
            <div className="flex justify-between border-b border-border/30 py-2">
              <dt className="text-muted-foreground">API URL</dt>
              <dd className="font-mono text-xs">{import.meta.env.VITE_API_URL || "http://localhost:8000"}</dd>
            </div>
            <div className="flex justify-between py-2">
              <dt className="text-muted-foreground">Organization ID</dt>
              <dd className="font-mono text-xs truncate max-w-[200px]">{user?.organization_id}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
