import { useCallback, useEffect, useRef, useState } from "react";
import { pollJob, submitGeneration } from "../api/client";
import type { GenerationRequest, GenerationResponse, GenerationStatus } from "../types";

const TERMINAL: GenerationStatus[] = ["complete", "failed"];
const POLL_MS = 2000;

export function useSceneJob() {
  const [response, setResponse] = useState<GenerationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  useEffect(() => () => stopPolling(), []);

  const generate = useCallback(async (req: GenerationRequest) => {
    setLoading(true);
    setError(null);
    setResponse(null);
    stopPolling();

    try {
      const initial = await submitGeneration(req);
      setResponse(initial);

      intervalRef.current = setInterval(async () => {
        try {
          const updated = await pollJob(initial.job_id);
          setResponse(updated);
          if (TERMINAL.includes(updated.status)) {
            stopPolling();
            setLoading(false);
            if (updated.status === "failed") {
              setError(updated.error ?? "Generation failed");
            }
          }
        } catch (e) {
          stopPolling();
          setLoading(false);
          setError(String(e));
        }
      }, POLL_MS);
    } catch (e) {
      setLoading(false);
      setError(String(e));
    }
  }, []);

  return { response, loading, error, generate };
}
