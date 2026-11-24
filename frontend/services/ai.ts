import { api } from "@/services/api";
import type { ItineraryDetail } from "@/types/itinerary";

export type AIStatus = { provider: "offline" | "claude"; label: string; sends_data_off_device: boolean; configured_provider: string; model: string | null; claude_sdk_installed: boolean };
export type FieldSuggestion = {
  field: string; label: string; value: unknown; display: string; merge: "replace" | "union" | "append";
  evidence: string | null; current: string | null; overwrites: boolean;
};
export type ReadResult = {
  provider: string; provider_label: string; sends_data_off_device: boolean; fallback_note: string | null;
  suggestions: FieldSuggestion[]; unmatched_places: string[]; special_requests: string[];
};
export type Suggestion = { key: string; kind: string; title: string; reason: string; action: Record<string, unknown> };

export const aiApi = {
  status: () => api.get<AIStatus>("/ai/status"),
  readText: (enquiryId: number, text: string) => api.post<ReadResult>(`/enquiries/${enquiryId}/requirements/read-text`, { text }),
  suggestions: (id: number, version?: number) => api.get<Suggestion[]>(`/itineraries/${id}/suggestions`, version ? { version } : undefined),
  apply: (id: number, key: string) => api.post<ItineraryDetail>(`/itineraries/${id}/suggestions/apply`, { key }),
};
