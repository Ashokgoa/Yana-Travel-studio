import { api, type QueryParams } from "@/services/api";
import type { Page } from "@/types/crm";
import type { ItineraryDetail, ItinerarySummary, Strategy } from "@/types/itinerary";

export const itinerariesApi = {
  generate: (enquiryId: number, strategies?: Strategy[]) =>
    api.post<ItinerarySummary[]>(`/enquiries/${enquiryId}/itineraries/generate`, strategies ? { strategies } : undefined),
  forEnquiry: (enquiryId: number) => api.get<ItinerarySummary[]>(`/enquiries/${enquiryId}/itineraries`),
  list: (params?: QueryParams) => api.get<Page<ItinerarySummary>>("/itineraries", params),
  get: (id: number) => api.get<ItineraryDetail>(`/itineraries/${id}`),
};
