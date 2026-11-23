import type { ApiErrorBody, HealthResponse } from "@/types/api";

/** Backend base URL; configured via NEXT_PUBLIC_API_BASE_URL (see .env.example). */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: ApiErrorBody,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Cannot reach the YANA backend. Is it running on port 8000?", 0);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => undefined)) as ApiErrorBody | undefined;
    throw new ApiError(body?.message ?? `Request failed (${response.status})`, response.status, body);
  }
  return (await response.json()) as T;
}

export const systemApi = {
  health: () => apiFetch<HealthResponse>("/health", { cache: "no-store" }),
};
