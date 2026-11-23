import { api, type QueryParams } from "@/services/api";
import type { Page } from "@/types/crm";
import type { Hotel, InventoryItem, InventoryOptions, ResourceKey, VehicleCategory } from "@/types/inventory";

const base = "/inventory";

export const inventoryApi = {
  options: () => api.get<InventoryOptions>(`${base}/options`),
  vehicleCategories: () => api.get<VehicleCategory[]>(`${base}/vehicle-categories`),

  list: (resource: ResourceKey, params?: QueryParams) => api.get<Page<InventoryItem>>(`${base}/${resource}`, params),
  get: (resource: ResourceKey, id: number) => api.get<InventoryItem>(`${base}/${resource}/${id}`),
  create: (resource: ResourceKey, body: Record<string, unknown>) => api.post<InventoryItem>(`${base}/${resource}`, body),
  update: (resource: ResourceKey, id: number, body: Record<string, unknown>) =>
    api.put<InventoryItem>(`${base}/${resource}/${id}`, body),
  setActive: (resource: ResourceKey, id: number, is_active: boolean) =>
    api.patch<InventoryItem>(`${base}/${resource}/${id}/status`, { is_active }),

  addRoomType: (hotelId: number, body: Record<string, unknown>) => api.post<Hotel>(`${base}/hotels/${hotelId}/room-types`, body),
  updateRoomType: (hotelId: number, id: number, body: Record<string, unknown>) =>
    api.put<Hotel>(`${base}/hotels/${hotelId}/room-types/${id}`, body),
  deleteRoomType: (hotelId: number, id: number) =>
    api.delete<Hotel>(`${base}/hotels/${hotelId}/room-types/${id}`),
  addRate: (hotelId: number, body: Record<string, unknown>) => api.post<Hotel>(`${base}/hotels/${hotelId}/rates`, body),
  updateRate: (hotelId: number, id: number, body: Record<string, unknown>) => api.put<Hotel>(`${base}/hotels/${hotelId}/rates/${id}`, body),
  deleteRate: (hotelId: number, id: number) => api.delete<Hotel>(`${base}/hotels/${hotelId}/rates/${id}`),
};
