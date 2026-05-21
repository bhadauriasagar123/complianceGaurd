export interface User {
  id: string;
  email: string;
  full_name: string;
  is_verified: boolean;
  mfa_enabled: boolean;
  role: string;
  organization_id: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthorizedTarget {
  id: string;
  target_value: string;
  target_type: string;
  normalized_target: string;
  is_active: boolean;
  verification_method: string;
  consent_recorded_at: string;
  created_at: string;
}

export interface Scan {
  id: string;
  target_value: string;
  scan_type: string;
  status: string;
  progress_percent: number;
  current_phase: string | null;
  scanners_enabled: string[];
  compliance_score: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  error_message: string | null;
}

export interface ScanListResponse {
  items: Scan[];
  total: number;
  page: number;
  page_size: number;
}

export interface Finding {
  id: string;
  scanner: string;
  category: string;
  severity: string;
  cvss_score: number | null;
  title: string;
  description: string;
  affected_asset: string;
  evidence: string | null;
  remediation: string | null;
  compliance_mappings: Record<string, unknown> | null;
  cwe_id: string | null;
  cve_id: string | null;
  ai_remediation: string | null;
  ai_confidence: number | null;
  created_at: string;
}

export interface FindingResolutionGuide {
  finding_id: string;
  summary: string;
  priority: string;
  estimated_effort: string;
  steps: ResolutionStep[];
  compliance_notes: string;
  confidence: number;
  powered_by_ai: boolean;
  ai_provider?: string | null;
}

export interface ResolutionStep {
  order: number;
  title: string;
  description: string;
  verification: string;
}

export interface AuditLog {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  outcome: string;
  message: string | null;
  created_at: string | null;
}

export type ScanType =
  | "infrastructure"
  | "web_application"
  | "api"
  | "container"
  | "full_assessment";

export type ScannerType =
  | "nmap"
  | "nuclei"
  | "zap"
  | "trivy"
  | "semgrep"
  | "bandit"
  | "gitleaks";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface ScanProgressMessage {
  scan_id: string;
  status: string;
  progress_percent: number;
  current_phase: string | null;
  compliance_score: number | null;
}
