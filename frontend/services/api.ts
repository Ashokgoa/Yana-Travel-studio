import type { ApiErrorBody, HealthResponse } from "@/types/api";

/**
 * Same-origin path: the Next server proxies /api/v1/* to the backend (see
 * next.config.ts). Works from this laptop and from other machines alike.
 */
export const API_BASE_URL = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: ApiErrorBody,
  ) {
    super(message);
  }
}

export type QueryParams = Record<string, string | number | boolean | null | undefined>;

export function withQuery(path: string, params?: QueryParams): string {
  if (!params) return path;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `${path}?${qs}` : path;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  // FormData bodies (uploads) must let the browser set the multipart boundary header.
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include", // send the HttpOnly session cookie
      headers: isForm ? init?.headers : { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Cannot reach YANA Travel Studio. Check your network connection.", 0);
  }
  if (response.status === 500 && !response.headers.get("content-type")?.includes("application/json")) {
    // Our backend always answers with JSON; a non-JSON 500 comes from the Next
    // proxy when the backend itself is not running.
    throw new ApiError("The YANA backend is not running. Start it with scripts\\start.ps1.", 503);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => undefined)) as ApiErrorBody | undefined;
    throw new ApiError(body?.message ?? `Request failed (${response.status})`, response.status, body);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, params?: QueryParams) => apiFetch<T>(withQuery(path, params), { cache: "no-store" }),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => apiFetch<T>(path, { method: "POST", body: form }),
};

export const systemApi = {
  health: () => api.get<HealthResponse>("/health"),
};
