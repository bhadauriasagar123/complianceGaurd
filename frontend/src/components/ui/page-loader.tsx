import { ShieldCheck } from "lucide-react";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

interface PageLoaderProps {
  message?: string;
}

export function PageLoader({ message = "Loading…" }: PageLoaderProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background cyber-grid gap-6 p-4">
      <ShieldCheck className="h-10 w-10 text-cyan-400/80" aria-hidden />
      <LoadingSpinner size="lg" label={message} />
    </div>
  );
}
