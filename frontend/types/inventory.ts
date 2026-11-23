// Mirrors backend/app/schemas/inventory.py

export const RESOURCE_KEYS = ["countries", "cities", "attractions", "hotels", "restaurants", "vehicles", "suppliers"] as const;
export type ResourceKey = (typeof RESOURCE_KEYS)[number];

export type CountryRef = { id: number; name: string; iso_code: string };
export type CityRef = { id: number; name: string; country: CountryRef };
export type SupplierRef = { id: number; name: string; supplier_type: string };

/** Fields every inventory row has; the rest is described by the resource config. */
export type InventoryItem = {
  id: number;
  name: string;
  is_active: boolean;
  is_demo?: boolean;
  created_at: string;
  updated_at: string;
  primary_image_url: string | null;
  country?: CountryRef | null;
  city?: CityRef;
  supplier?: SupplierRef | null;
  [key: string]: unknown;
};

export type RoomType = {
  id: number;
  name: string;
  max_occupancy: number;
  bed_config: string | null;
  base_price: string | null;
  currency: string;
  price_is_verified: boolean;
};

export type SeasonalRate = {
  id: number;
  room_type_id: number;
  season_name: string;
  valid_from: string;
  valid_to: string;
  price: string;
  currency: string;
  is_verified: boolean;
};

export type Hotel = InventoryItem & { room_types: RoomType[]; rates: SeasonalRate[] };

export type VehicleCategory = { id: number; code: string; name: string; passenger_capacity: number; luggage_capacity: number | null };

export type InventoryOptions = {
  attraction_categories: string[];
  interest_tags: string[];
  hotel_styles: string[];
  hotel_facilities: string[];
  weekdays: string[];
  price_ranges: string[];
  supplier_types: string[];
  location_types: string[];
  attraction_settings: string[];
  service_types: string[];
};
