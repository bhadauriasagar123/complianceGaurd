import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/store/authStore";

/**
 * In dev, use relative URLs so Vite proxies /api → backend (no CORS).
 * Set VITE_API_URL only for production or direct API access.
 */
function resolveApiRoot(): string {
  const configured = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (import.meta.env.DEV) return "";
  return "http://localhost:8000";
}

export const API_BASE_URL = resolveApiRoot();

export const API_V1_BASE = API_BASE_URL ? `${API_BASE_URL}/api/v1` : "/api/v1";

export const CSRF_COOKIE_NAME = "cg_csrf_token";
export const CSRF_HEADER_NAME = "X-CSRF-Token";

const CSRF_STORAGE_KEY = "cg_csrf_token";

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/** CSRF token: sessionStorage for cross-origin API (Vercel→Render), else cookie (dev proxy). */
function getCsrfToken(): string | null {
  try {
    const stored = sessionStorage.getItem(CSRF_STORAGE_KEY);
    if (stored) return stored;
  } catch {
    /* private mode */
  }
  return getCookie(CSRF_COOKIE_NAME);
}

export const apiClient = axios.create({
  baseURL: API_V1_BASE,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

/** Prime CSRF token (cookie + sessionStorage for cross-origin production). */
export async function ensureCsrfCookie(): Promise<void> {
  const url = API_BASE_URL
    ? `${API_BASE_URL}/api/v1/auth/csrf`
    : "/api/v1/auth/csrf";
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    throw new Error(`CSRF bootstrap failed: ${res.status}`);
  }
  const data = (await res.json()) as { csrf_token?: string };
  if (data.csrf_token) {
    try {
      sessionStorage.setItem(CSRF_STORAGE_KEY, data.csrf_token);
    } catch {
      /* ignore */
    }
  }
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }

  const method = (config.method ?? "get").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      config.headers.set(CSRF_HEADER_NAME, csrf);
    }
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  try {
    const { data } = await apiClient.post<{ access_token: string }>("/auth/refresh", {});
    useAuthStore.getState().setAccessToken(data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const isAuthBootstrap =
      original?.url?.includes("/auth/me") || original?.url?.includes("/auth/refresh");
    const hadBearer = Boolean(
      original?.headers?.get?.("Authorization") ?? original?.headers?.Authorization
    );

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !original.url?.includes("/auth/login") &&
      !original.url?.includes("/auth/register") &&
      !original.url?.includes("/auth/refresh") &&
      !isAuthBootstrap &&
      hadBearer
    ) {
      original._retry = true;
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      const token = await refreshPromise;
      if (token) {
        original.headers.set("Authorization", `Bearer ${token}`);
        return apiClient(original);
      }
      window.dispatchEvent(new CustomEvent("auth:logout"));
    }
    return Promise.reject(error);
  }
);

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as { detail?: string | { msg: string }[] };
    if (typeof detail?.detail === "string") return detail.detail;
    if (Array.isArray(detail?.detail)) {
      return detail.detail.map((d) => d.msg).join(", ");
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred";
}

export function getWebSocketUrl(scanId: string, token: string): string {
  if (import.meta.env.DEV && !import.meta.env.VITE_API_URL) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/api/v1/ws/scans/${scanId}?token=${encodeURIComponent(token)}`;
  }
  const base = API_BASE_URL.replace(/^http/, "ws");
  return `${base}/api/v1/ws/scans/${scanId}?token=${encodeURIComponent(token)}`;
}
