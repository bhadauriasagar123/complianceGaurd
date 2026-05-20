import { apiClient } from "@/lib/api";
import type {
  AuthorizedTarget,
  Finding,
  Scan,
  ScanListResponse,
  ScanType,
  ScannerType,
} from "@/types";

export interface CreateTargetPayload {
  target_value: string;
  target_type: "url" | "domain" | "ip" | "cidr";
  ownership_proof?: string;
  verification_method: string;
  consent_confirmed: boolean;
  notes?: string;
}

export interface CreateScanPayload {
  authorized_target_id: string;
  scan_type: ScanType;
  scanners_enabled: ScannerType[];
  consent_confirmed: boolean;
}

export const scansApi = {
  listTargets: async (): Promise<AuthorizedTarget[]> => {
    const { data } = await apiClient.get<AuthorizedTarget[]>("/targets");
    return data;
  },

  createTarget: async (payload: CreateTargetPayload): Promise<AuthorizedTarget> => {
    const { data } = await apiClient.post<AuthorizedTarget>("/targets", payload);
    return data;
  },

  listScans: async (params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<ScanListResponse> => {
    const { data } = await apiClient.get<ScanListResponse>("/scans", { params });
    return data;
  },

  getScan: async (scanId: string): Promise<Scan> => {
    const { data } = await apiClient.get<Scan>(`/scans/${scanId}`);
    return data;
  },

  createScan: async (payload: CreateScanPayload): Promise<Scan> => {
    const { data } = await apiClient.post<Scan>("/scans", payload);
    return data;
  },

  cancelScan: async (scanId: string): Promise<Scan> => {
    const { data } = await apiClient.post<Scan>(`/scans/${scanId}/cancel`);
    return data;
  },

  getFindings: async (
    scanId: string,
    severity?: string
  ): Promise<Finding[]> => {
    const { data } = await apiClient.get<Finding[]>(`/scans/${scanId}/findings`, {
      params: severity ? { severity } : undefined,
    });
    return data;
  },
};
