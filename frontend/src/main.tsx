import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { useAuthStore } from "./store/authStore";
import { authApi } from "./api/auth";
import { ensureCsrfCookie } from "./lib/api";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const { setUser, setLoading, logout } = useAuthStore();

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      setLoading(true);
      try {
        await ensureCsrfCookie();
        const token = useAuthStore.getState().accessToken;
        if (!token) {
          return;
        }
        const user = await authApi.getMe();
        if (!cancelled) {
          setUser(user);
        }
      } catch {
        if (!cancelled) {
          logout();
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    const onLogout = () => {
      logout();
    };

    window.addEventListener("auth:logout", onLogout);
    init();

    return () => {
      cancelled = true;
      window.removeEventListener("auth:logout", onLogout);
    };
  }, [setUser, setLoading, logout]);

  return <>{children}</>;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AuthBootstrap>
          <App />
        </AuthBootstrap>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
