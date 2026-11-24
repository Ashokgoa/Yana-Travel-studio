import { api, type QueryParams } from "@/services/api";
import type { Page } from "@/types/crm";
import type { ItineraryDetail, ItinerarySummary, Strategy, TimeSlot, VersionDiff, VersionInfo } from "@/types/itinerary";

const base = (id: number) => `/itineraries/${id}`;

export const itinerariesApi = {
  generate: (enquiryId: number, strategies?: Strategy[]) =>
    api.post<ItinerarySummary[]>(`/enquiries/${enquiryId}/itineraries/generate`, strategies ? { strategies } : undefined),
  forEnquiry: (enquiryId: number) => api.get<ItinerarySummary[]>(`/enquiries/${enquiryId}/itineraries`),
  list: (params?: QueryParams) => api.get<Page<ItinerarySummary>>("/itineraries", params),
  get: (id: number, version?: number) => api.get<ItineraryDetail>(base(id), version ? { version } : undefined),

  // versions
  versions: (id: number) => api.get<VersionInfo[]>(`${base(id)}/versions`),
  compare: (id: number, a: number, b: number) => api.get<VersionDiff>(`${base(id)}/versions/compare`, { a, b }),
  startEditing: (id: number) => api.post<ItineraryDetail>(`${base(id)}/edit`),
  saveVersion: (id: number, label: string, notes?: string) => api.post<ItineraryDetail>(`${base(id)}/versions`, { label, notes }),
  restore: (id: number, version: number) => api.post<ItineraryDetail>(`${base(id)}/versions/${version}/restore`),
  duplicate: (id: number) => api.post<ItinerarySummary>(`${base(id)}/duplicate`),

  // edits (working copy)
  addDayAfter: (id: number, day: number) => api.post<ItineraryDetail>(`${base(id)}/days/${day}/add-after`),
  duplicateDay: (id: number, day: number) => api.post<ItineraryDetail>(`${base(id)}/days/${day}/duplicate`),
  removeDay: (id: number, day: number) => api.delete<ItineraryDetail>(`${base(id)}/days/${day}`),
  updateDay: (id: number, day: number, body: { title?: string; description?: string | null }) =>
    api.patch<ItineraryDetail>(`${base(id)}/days/${day}`, body),
  addActivity: (id: number, day: number, body: { time_slot: TimeSlot; attraction_id?: number; activity_type?: string; title?: string; description?: string; duration_min?: number }) =>
    api.post<ItineraryDetail>(`${base(id)}/days/${day}/activities`, body),
  updateActivity: (id: number, activityId: number, body: { title?: string; description?: string | null; time_slot?: TimeSlot; duration_min?: number | null }) =>
    api.patch<ItineraryDetail>(`${base(id)}/activities/${activityId}`, body),
  moveActivity: (id: number, activityId: number, body: { day_number: number; position: number; time_slot?: TimeSlot }) =>
    api.post<ItineraryDetail>(`${base(id)}/activities/${activityId}/move`, body),
  removeActivity: (id: number, activityId: number) => api.delete<ItineraryDetail>(`${base(id)}/activities/${activityId}`),
  setMeal: (id: number, day: number, meal: string, body: { arrangement: string; restaurant_id?: number | null }) =>
    api.put<ItineraryDetail>(`${base(id)}/days/${day}/meals/${meal}`, body),
  replaceHotel: (id: number, stayId: number, hotelId: number) => api.put<ItineraryDetail>(`${base(id)}/stays/${stayId}/hotel`, { hotel_id: hotelId }),
  setVehicle: (id: number, vehicleId: number | null) => api.put<ItineraryDetail>(`${base(id)}/vehicle`, { vehicle_id: vehicleId }),
  setLegMode: (id: number, transportId: number, mode: string) => api.patch<ItineraryDetail>(`${base(id)}/transports/${transportId}`, { mode }),
};
