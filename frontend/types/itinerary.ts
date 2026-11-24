// Mirrors backend/app/schemas/itinerary.py
export type Strategy = "classic" | "scenic" | "premium";

export type RouteStop = { city_id: number; city: string; country: string; iso_code: string; nights: number; lat: number | null; lng: number | null };
export type HotelRef = { id: number; name: string; stars: number | null; is_demo: boolean; image_url: string | null };
export type CostLine = { category: string; description: string; amount: string | null; currency: string; is_estimate: boolean };

export type ItinerarySummary = {
  id: number;
  enquiry_id: number | null;
  enquiry_reference: string | null;
  customer_name: string | null;
  title: string;
  strategy: Strategy;
  strategy_summary: string;
  status: string;
  batch: number;
  created_at: string;
  version_number: number;
  version_label: string;
  version_notes: string | null;
  is_locked: boolean;
  latest_version_number: number;
  start_date: string;
  total_days: number;
  total_nights: number;
  route: RouteStop[];
  hotels: (HotelRef | null)[];
  total_cost: string | null;
  cost_per_person: string | null;
  currency: string;
  unknown_cost_items: number;
  total_distance_km: number;
  warnings_count: number;
};

export type Activity = {
  id: number;
  time_slot: "morning" | "afternoon" | "evening" | "full_day";
  activity_type: string;
  title: string;
  description: string | null;
  duration_min: number | null;
  attraction_id: number | null;
  image_url: string | null;
};
export type Meal = { id: number; meal: string; arrangement: string; restaurant_id: number | null; restaurant_name: string | null; cuisine: string | null; note: string | null };
export type Day = { id: number; day_number: number; date: string; city_id: number; city: string; overnight_city: string | null; title: string; description: string | null; activities: Activity[]; meals: Meal[] };
export type Stay = {
  id: number; city_id: number; city: string; check_in_day: number; nights: number; hotel: HotelRef | null;
  rooms: { room_type_id: number | null; label: string; count: number; price: string | null }[];
  alternatives: HotelRef[]; estimated_cost: string | null; note: string | null;
};
export type Transport = {
  id: number; day_number: number; kind: string; mode: string; from_city: string | null; to_city: string | null; vehicle: string | null;
  distance_km: number | null; duration_min: number | null; is_estimate: boolean; note: string | null;
};

export type ItineraryDetail = ItinerarySummary & {
  explanations: string[];
  warnings: string[];
  costs: CostLine[];
  vehicle: string | null;
  days: Day[];
  stays: Stay[];
  transports: Transport[];
};

// ------------------------------------------------------------------ builder (Phase 5)
export type TimeSlot = "morning" | "afternoon" | "full_day" | "evening";

export type VersionInfo = {
  version_number: number;
  label: string;
  notes: string | null;
  is_locked: boolean;
  created_at: string;
  created_by: string | null;
  total_days: number;
  total_nights: number;
  total_cost: string | null;
  currency: string;
};

export type VersionDiff = {
  a: number;
  b: number;
  summary: string[];
  route_a: string[];
  route_b: string[];
  cost_a: string | null;
  cost_b: string | null;
  currency: string;
};
