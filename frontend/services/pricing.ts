import { api, withQuery } from "@/services/api";
import type { ManualLine, PricingDefaults, PricingUpdate, PricingView } from "@/types/pricing";

const base = (id: number, version?: number, path = "") => withQuery(`/itineraries/${id}/pricing${path}`, version ? { version } : undefined);

export const pricingApi = {
  get: (id: number, version?: number) => api.get<PricingView>(base(id, version)),
  update: (id: number, body: PricingUpdate, version?: number) => api.patch<PricingView>(base(id, version), body),
  override: (id: number, body: { key: string; unit_cost?: string | null; clear_unit_cost?: boolean; quantity?: string; included?: boolean }, version?: number) =>
    api.put<PricingView>(base(id, version, "/overrides"), body),
  resetOverride: (id: number, key: string, version?: number) =>
    api.delete<PricingView>(withQuery(`/itineraries/${id}/pricing/overrides`, { key, version })),
  stayRate: (id: number, body: { key: string; double_rate?: string | null; single_rate?: string | null }, version?: number) =>
    api.put<PricingView>(base(id, version, "/stay-rates"), body),
  addLine: (id: number, body: ManualLine, version?: number) => api.post<PricingView>(base(id, version, "/lines"), body),
  updateLine: (id: number, lineId: number, body: ManualLine, version?: number) => api.put<PricingView>(base(id, version, `/lines/${lineId}`), body),
  deleteLine: (id: number, lineId: number, version?: number) => api.delete<PricingView>(base(id, version, `/lines/${lineId}`)),
  defaults: () => api.get<PricingDefaults>("/settings/pricing"),
  saveDefaults: (body: PricingDefaults) => api.put<PricingDefaults>("/settings/pricing", body),
};
