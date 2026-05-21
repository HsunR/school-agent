/* ── Admin queue status polling hook ── */

"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export interface QueueStatus {
  busy: boolean;
  pending: number;
  current_task: string | null;
  progress: number;
  total: number;
}

interface UseQueueStatusOptions {
  onIdle?: () => void;
}

const POLL_INTERVAL = 2000;

const IDLE_STATUS: QueueStatus = {
  busy: false,
  pending: 0,
  current_task: null,
  progress: 0,
  total: 0,
};

export function useQueueStatus(options?: UseQueueStatusOptions) {
  const [status, setStatus] = useState<QueueStatus>(IDLE_STATUS);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onIdleRef = useRef(options?.onIdle);
  onIdleRef.current = options?.onIdle;

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/admin/queue");
      if (!res.ok) return;
      const data: QueueStatus = await res.json();
      setStatus(data);
      return data;
    } catch {
      // Ignore network errors
    } finally {
      setLoading(false);
    }
  }, []);

  const clearQueue = useCallback(async () => {
    try {
      await fetch("/api/admin/queue/clear", { method: "POST" });
    } catch {
      // Ignore network errors
    }
  }, []);

  useEffect(() => {
    fetchStatus();

    intervalRef.current = setInterval(async () => {
      const data = await fetchStatus();
      if (data && !data.busy && data.pending === 0) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        onIdleRef.current?.();
      }
    }, POLL_INTERVAL);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetchStatus]);

  return { status, clearQueue, loading };
}
