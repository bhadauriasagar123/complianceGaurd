import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";

interface LoadingOverlayProps {
  show: boolean;
  label?: string;
  className?: string;
  blur?: boolean;
}

/** Blocks interaction and shows a spinner over a card, modal, or form. */
export function LoadingOverlay({
  show,
  label = "Please wait…",
  className,
  blur = true,
}: LoadingOverlayProps) {
  if (!show) return null;

  return (
    <div
      className={cn(
        "absolute inset-0 z-20 flex items-center justify-center rounded-[inherit]",
        blur ? "bg-background/75 backdrop-blur-sm" : "bg-background/90",
        className
      )}
      aria-live="polite"
      aria-busy="true"
    >
      <LoadingSpinner size="md" label={label} />
    </div>
  );
}
