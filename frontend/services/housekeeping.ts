import { API_BASE_URL, api } from "@/services/api";
import type { ItinerarySummary } from "@/types/itinerary";

export type BackupInfo = { name: string; size_bytes: number; created_at: string; created_by: string | null; counts: Record<string, number>; files: number | null; alembic_revision: string | null; valid: boolean };
export type DemoSummary = Record<"hotels" | "restaurants" | "vehicles" | "sightseeing" | "suppliers", { demo: number; in_use: number | null }> & { total: number };
export type DemoResult = Record<string, { deleted: number; deactivated: number }>;

export const housekeepingApi = {
  backups: () => api.get<BackupInfo[]>("/admin/backups"),
  createBackup: () => api.post<BackupInfo>("/admin/backups"),
  deleteBackup: (name: string) => api.delete<void>(`/admin/backups/${encodeURIComponent(name)}`),
  backupUrl: (name: string) => `${API_BASE_URL}/admin/backups/${encodeURIComponent(name)}/download`,
  demoSummary: () => api.get<DemoSummary>("/admin/demo-data"),
  removeDemo: () => api.post<DemoResult>("/admin/demo-data/remove"),
  templates: () => api.get<ItinerarySummary[]>("/itinerary-templates"),
  saveAsTemplate: (id: number, body: { title: string; description?: string | null }, version?: number) =>
    api.post<ItinerarySummary>(`/itineraries/${id}/save-as-template${version ? `?version=${version}` : ""}`, body),
  archiveTemplate: (id: number) => api.delete<void>(`/itinerary-templates/${id}`),
  fromTemplate: (enquiryId: number, templateId: number) => api.post<ItinerarySummary>(`/enquiries/${enquiryId}/itineraries/from-template`, { template_id: templateId }),
};
