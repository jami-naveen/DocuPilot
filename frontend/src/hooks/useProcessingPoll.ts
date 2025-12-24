import { useEffect, useState } from "react";
import type { ProcessStatus } from "../types/api";
import { getProcessingStatus } from "../api/client";

export function useProcessingPoll(jobId: string | null, intervalMs = 2000) {
  const [status, setStatus] = useState<ProcessStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setStatus(null);
      return;
    }
    let isCancelled = false;
    const tick = async () => {
      try {
        const next = await getProcessingStatus(jobId);
        if (!isCancelled) {
          setStatus(next);
        }
        if (next.state === "completed" || next.state === "failed") {
          return;
        }
        setTimeout(tick, intervalMs);
      } catch (err) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      }
    };
    tick();
    return () => {
      isCancelled = true;
    };
  }, [jobId, intervalMs]);

  return { status, error };
}
