import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-8 w-8",
  lg: "h-12 w-12",
};

export function LoadingSpinner({ size = "md", className, label }: LoadingSpinnerProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3", className)} role="status">
      <Loader2 className={cn("animate-spin text-cyan-400", sizeClasses[size])} aria-hidden />
      {label && <p className="text-sm text-muted-foreground animate-pulse">{label}</p>}
      {label && <span className="sr-only">{label}</span>}
    </div>
  );
}
