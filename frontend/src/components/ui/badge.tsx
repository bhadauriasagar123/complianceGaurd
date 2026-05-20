import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
        critical: "border-red-500/30 bg-red-500/15 text-red-400",
        high: "border-orange-500/30 bg-orange-500/15 text-orange-400",
        medium: "border-yellow-500/30 bg-yellow-500/15 text-yellow-400",
        low: "border-blue-500/30 bg-blue-500/15 text-blue-400",
        info: "border-gray-500/30 bg-gray-500/15 text-gray-400",
        success: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400",
        warning: "border-amber-500/30 bg-amber-500/15 text-amber-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export function severityBadgeVariant(
  severity: string
): VariantProps<typeof badgeVariants>["variant"] {
  const map: Record<string, VariantProps<typeof badgeVariants>["variant"]> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
    info: "info",
  };
  return map[severity] ?? "secondary";
}

export { Badge, badgeVariants };
