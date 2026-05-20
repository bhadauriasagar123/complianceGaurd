import { useCallback, useEffect, useRef, useState } from "react";
import { getWebSocketUrl } from "@/lib/api";
import type { ScanProgressMessage } from "@/types";

interface UseScanWebSocketOptions {
  scanId: string | null;
  token: string | null;
  enabled?: boolean;
  onComplete?: (data: ScanProgressMessage) => void;
}

export function useScanWebSocket({
  scanId,
  token,
  enabled = true,
  onComplete,
}: UseScanWebSocketOptions) {
  const [progress, setProgress] = useState<ScanProgressMessage | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (!enabled || !scanId || !token) {
      disconnect();
      setProgress(null);
      return;
    }

    const url = getWebSocketUrl(scanId, token);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ScanProgressMessage;
        setProgress(data);
        if (["completed", "failed", "cancelled"].includes(data.status)) {
          onCompleteRef.current?.(data);
          ws.close();
        }
      } catch {
        setError("Invalid progress message");
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error");
      setConnected(false);
    };

    ws.onclose = () => {
      setConnected(false);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [scanId, token, enabled, disconnect]);

  return { progress, connected, error, disconnect };
}
