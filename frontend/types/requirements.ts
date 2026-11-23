// Mirrors backend/app/schemas/requirements.py
import type { CityRef, CountryRef } from "@/types/inventory";

export type Preference = "mandatory" | "preferred" | "optional" | "avoid";

export type DestinationInput = { country_id: number; city_id: number | null; preference: Preference; min_nights: number | null };
export type Destination = { id: number; country: CountryRef; city: CityRef | null; preference: Preference; min_nights: number | null; sort_order: number };
export type RoomLine = { type: string; count: number };

type Shared = {
  adults: number;
  children: number;
  children_ages: number[];
  arrival_date: string | null;
  departure_date: string | null;
  arrival_airport: string | null;
  departure_airport: string | null;
  start_country_id: number | null;
  end_country_id: number | null;
  travel_type: "FIT" | "GIT" | null;
  group_size: number | null;
  interests: string[];
  travel_pace: string | null;
  hotel_categories: string[];
  hotel_locations: string[];
  breakfast_required: boolean;
  rooms: RoomLine[];
  food_preferences: string[];
  meals: string[];
  transport_modes: string[];
  passenger_capacity: number | null;
  luggage_notes: string | null;
  airport_transfers: boolean;
  local_sightseeing_transport: boolean;
  budget_per_person: string | null;
  budget_total: string | null;
  currency: string;
  budget_flexibility: string | null;
  travel_class: string | null;
  additional_requirements: string | null;
  internal_notes: string | null;
  completed_steps: number[];
};

export type RequirementInput = Shared & { destinations: DestinationInput[] };

export type Requirement = Shared & {
  enquiry_id: number;
  exists: boolean;
  destinations: Destination[];
  updated_at: string | null;
  total_days: number | null;
  total_nights: number | null;
  total_travellers: number;
  rooms_count: number;
  room_capacity: number;
  missing: string[];
  warnings: string[];
  is_complete: boolean;
};

export type RequirementOptions = {
  preferences: Preference[];
  interests: string[];
  hotel_categories: string[];
  hotel_locations: string[];
  room_types: string[];
  food_preferences: string[];
  meals: string[];
  transport_modes: string[];
  travel_paces: string[];
  budget_flexibility: string[];
  travel_classes: string[];
};
