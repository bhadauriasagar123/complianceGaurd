import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(date));
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value)}%`;
}

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
  info: "#6b7280",
};

export const SCAN_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  validating: "Validating",
  queued: "Queued",
  running: "Running",
  normalizing: "Normalizing",
  ai_processing: "AI Processing",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};
