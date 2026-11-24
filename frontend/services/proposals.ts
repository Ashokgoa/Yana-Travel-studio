import { API_BASE_URL, ApiError, api, withQuery } from "@/services/api";
import type { ApiErrorBody } from "@/types/api";
import type { BrandingSettings, ProposalExport, ProposalOptions, ProposalSettings } from "@/types/proposal";

const base = (id: number) => `/itineraries/${id}/proposal`;

export const proposalsApi = {
  settings: (id: number) => api.get<ProposalSettings>(`${base(id)}/settings`),
  saveSettings: (id: number, body: ProposalSettings) => api.put<ProposalSettings>(`${base(id)}/settings`, body),
  options: (id: number, version?: number) => api.get<ProposalOptions>(`${base(id)}/options`, version ? { version } : undefined),
  /** Live preview HTML (static, no scripts). Aborted when settings change again. */
  preview: async (id: number, body: ProposalSettings, version?: number, signal?: AbortSignal): Promise<string> => {
    const res = await fetch(`${API_BASE_URL}${withQuery(`${base(id)}/preview`, version ? { version } : undefined)}`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => undefined)) as ApiErrorBody | undefined;
      throw new ApiError(err?.message ?? `Preview failed (${res.status})`, res.status, err);
    }
    return res.text();
  },
  exportPdf: (id: number, body: ProposalSettings, version?: number) =>
    api.post<ProposalExport>(withQuery(`${base(id)}/export`, version ? { version } : undefined), body),
  exports: (id: number) => api.get<ProposalExport[]>(`${base(id)}/exports`),
  fileUrl: (id: number, exportId: number) => `${API_BASE_URL}${base(id)}/exports/${exportId}/file`,
  branding: () => api.get<BrandingSettings>("/settings/branding"),
  saveBranding: (body: BrandingSettings) => api.put<BrandingSettings>("/settings/branding", body),
};
