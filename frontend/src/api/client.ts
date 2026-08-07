import type { GenerationRequest, GenerationResponse } from "../types";

const BASE = "/api/v1";

export async function submitGeneration(
  req: GenerationRequest
): Promise<GenerationResponse> {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function pollJob(jobId: string): Promise<GenerationResponse> {
  const res = await fetch(`${BASE}/generate/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
