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
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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
    let active = true;

    const poll = async () => {
      const data = await fetchStatus();
      if (!active) return;
      if (data && !data.busy && data.pending === 0) {
        onIdleRef.current?.();
        return;
      }
      if (active) {
        timeoutRef.current = setTimeout(poll, POLL_INTERVAL);
      }
    };

    fetchStatus();
    timeoutRef.current = setTimeout(poll, POLL_INTERVAL);

    return () => {
      active = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [fetchStatus]);

  return { status, clearQueue, loading };
}
