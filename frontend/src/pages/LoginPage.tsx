import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { ShieldCheck, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingOverlay } from "@/components/ui/loading-overlay";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
import { getApiErrorMessage } from "@/lib/api";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
  mfa_code: z.string().length(6, "MFA code must be 6 digits").optional().or(z.literal("")),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { setUser, setAccessToken, setLoading } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [showMfa, setShowMfa] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    if (isSubmitting) return;
    setError(null);
    setLoading(true);
    try {
      const tokenRes = await authApi.login({
        email: data.email,
        password: data.password,
        mfa_code: data.mfa_code || undefined,
      });
      setAccessToken(tokenRes.access_token);
      const user = await authApi.getMe();
      setUser(user);
      navigate("/dashboard");
    } catch (err) {
      const msg = getApiErrorMessage(err);
      if (msg.toLowerCase().includes("mfa")) {
        setShowMfa(true);
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background cyber-grid p-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="mb-8 flex flex-col items-center gap-2">
          <ShieldCheck className="h-12 w-12 text-cyan-400" aria-hidden />
          <h1 className="text-2xl font-bold">Sign in to ComplianceGuard</h1>
        </div>

        <Card className="glow-cyan border-cyan-500/20 relative overflow-hidden">
          <LoadingOverlay show={isSubmitting} label="Signing in…" />
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>Enter your credentials to access the dashboard</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-4"
              noValidate
              aria-busy={isSubmitting}
            >
              {error && (
                <div
                  className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                  role="alert"
                >
                  {error}
                </div>
              )}
              <div>
                <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  disabled={isSubmitting}
                  {...register("email")}
                  error={errors.email?.message}
                />
              </div>
              <div>
                <label htmlFor="password" className="mb-1.5 block text-sm font-medium">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  disabled={isSubmitting}
                  {...register("password")}
                  error={errors.password?.message}
                />
              </div>
              {showMfa && (
                <div>
                  <label htmlFor="mfa_code" className="mb-1.5 block text-sm font-medium">
                    MFA code
                  </label>
                  <Input
                    id="mfa_code"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    autoComplete="one-time-code"
                    disabled={isSubmitting}
                    {...register("mfa_code")}
                    error={errors.mfa_code?.message}
                  />
                </div>
              )}
              <Button type="submit" className="w-full" variant="cyber" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  "Sign in"
                )}
              </Button>
            </form>
            <p className="mt-6 text-center text-sm text-muted-foreground">
              No account?{" "}
              <Link to="/register" className="text-cyan-400 hover:underline">
                Create one
              </Link>
            </p>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
