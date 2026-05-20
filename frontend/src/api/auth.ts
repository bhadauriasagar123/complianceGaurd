import { apiClient } from "@/lib/api";
import type { TokenResponse, User } from "@/types";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  mfa_code?: string;
  organization_slug?: string;
}

export const authApi = {
  register: async (payload: RegisterPayload): Promise<User> => {
    const { data } = await apiClient.post<User>("/auth/register", payload);
    return data;
  },

  login: async (payload: LoginPayload): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
    return data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },

  refresh: async (): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>("/auth/refresh", {});
    return data;
  },

  getMe: async (): Promise<User> => {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },

  setupMfa: async (): Promise<{
    secret: string;
    provisioning_uri: string;
    qr_code_base64: string;
  }> => {
    const { data } = await apiClient.post("/auth/mfa/setup");
    return data;
  },

  enableMfa: async (code: string): Promise<void> => {
    await apiClient.post("/auth/mfa/enable", { code });
  },
};
