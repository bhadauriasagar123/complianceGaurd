import { apiClient } from "@/lib/api";
import type { AuditLog } from "@/types";

export const auditApi = {
  listLogs: async (params?: {
    page?: number;
    page_size?: number;
    action?: string;
  }): Promise<AuditLog[]> => {
    const { data } = await apiClient.get<AuditLog[]>("/audit/logs", { params });
    return data;
  },
};
