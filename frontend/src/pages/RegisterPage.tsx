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
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { authApi } from "@/api/auth";
import { getApiErrorMessage } from "@/lib/api";

const passwordRegex =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{12,}$/;

const registerSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z
    .string()
    .min(12, "At least 12 characters")
    .regex(
      passwordRegex,
      "Must include uppercase, lowercase, digit, and special character"
    ),
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  organization_name: z.string().min(2, "Organization name required"),
});

type RegisterForm = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    if (isSubmitting) return;
    setError(null);
    try {
      await authApi.register(data);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(getApiErrorMessage(err));
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
          <h1 className="text-2xl font-bold">Create your account</h1>
        </div>

        <Card className="border-cyan-500/20 relative overflow-hidden">
          <LoadingOverlay show={isSubmitting} label="Creating your account…" />
          <CardHeader>
            <CardTitle>Register</CardTitle>
            <CardDescription>Start securing your infrastructure today</CardDescription>
          </CardHeader>
          <CardContent>
            {success ? (
              <div className="py-6">
                <LoadingSpinner size="md" label="Account created! Redirecting to sign in…" />
              </div>
            ) : (
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
                  <label htmlFor="full_name" className="mb-1.5 block text-sm font-medium">
                    Full name
                  </label>
                  <Input id="full_name" {...register("full_name")} error={errors.full_name?.message} />
                </div>
                <div>
                  <label htmlFor="organization_name" className="mb-1.5 block text-sm font-medium">
                    Organization
                  </label>
                  <Input
                    id="organization_name"
                    {...register("organization_name")}
                    error={errors.organization_name?.message}
                  />
                </div>
                <div>
                  <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
                    Email
                  </label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
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
                    autoComplete="new-password"
                    {...register("password")}
                    error={errors.password?.message}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    12+ chars with upper, lower, digit, and special character
                  </p>
                </div>
                <Button type="submit" className="w-full" variant="cyber" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Creating account…
                    </>
                  ) : (
                    "Create account"
                  )}
                </Button>
              </form>
            )}
            <p className="mt-6 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="text-cyan-400 hover:underline">
                Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
