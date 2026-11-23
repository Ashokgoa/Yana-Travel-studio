import { Bus, Building2, Hotel as HotelIcon, Landmark, MapPin, Truck, UtensilsCrossed, type LucideIcon } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { InventoryItem, InventoryOptions, ResourceKey } from "@/types/inventory";

// ------------------------------------------------------------------ labels
const LABELS: Record<string, string> = {
  city_centre: "City centre",
  historical_landmarks: "Historical landmarks",
  theme_park: "Theme park",
  theme_parks: "Theme parks",
  airport_transfer: "Airport transfer",
  long_distance: "Long distance",
  family_rooms: "Family rooms",
  accessible_rooms: "Accessible rooms",
  air_conditioning: "Air conditioning",
  airport_shuttle: "Airport shuttle",
  coach_parking: "Coach parking",
  meeting_rooms: "Meeting rooms",
  room_service: "Room service",
  wifi: "Wi‑Fi",
  mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun",
};

export function humanize(code: string): string {
  return LABELS[code] ?? code.charAt(0).toUpperCase() + code.slice(1).replace(/_/g, " ");
}

export const CURRENCIES = ["EUR", "GBP", "USD", "CHF", "INR", "AED"];

// ------------------------------------------------------------------ field model
export type RefSource = "countries" | "cities" | "suppliers" | "vehicleCategories";

export type FieldType =
  | "text" | "textarea" | "email" | "int" | "decimal" | "float"
  | "select" | "multi" | "tristate" | "bool" | "reference" | "multiref" | "currency";

export type FieldDef = {
  name: string;
  label: string;
  type: FieldType;
  section: string;
  required?: boolean;
  hint?: string;
  placeholder?: string;
  wide?: boolean;
  vocab?: keyof InventoryOptions;
  staticOptions?: [string, string][];
  ref?: RefSource;
  refFilter?: Record<string, string>;
  /** Read the form value from an item when it isn't simply item[name]. */
  get?: (item: InventoryItem) => unknown;
  /** Show only in the detail view (computed/read-only). */
  readOnly?: boolean;
};

export type ColumnDef = {
  header: string;
  render: (item: InventoryItem) => React.ReactNode;
  className?: string;
};

export type FilterDef = { param: string; label: string; vocab?: keyof InventoryOptions; ref?: RefSource; staticOptions?: [string, string][] };

export type ResourceConfig = {
  key: ResourceKey;
  title: string;
  singular: string;
  description: string;
  icon: LucideIcon;
  basePath: string;
  hasImages: boolean;
  searchPlaceholder: string;
  columns: ColumnDef[];
  filters: FilterDef[];
  fields: FieldDef[];
  subtitle?: (item: InventoryItem) => string;
};

// ------------------------------------------------------------------ helpers for columns
const cityCell = (i: InventoryItem) =>
  i.city ? (
    <span>
      {i.city.name}
      <span className="text-muted-foreground">, {i.city.country.iso_code}</span>
    </span>
  ) : "—";

const priceCell = (amount: unknown, currency: unknown, verified: unknown, suffix = "") =>
  amount ? (
    <span className="whitespace-nowrap">
      {formatMoney(String(amount), String(currency ?? "EUR"))}
      {suffix}
      {!verified && <span className="ml-1 text-[11px] text-muted-foreground">est.</span>}
    </span>
  ) : (
    <span className="text-muted-foreground">—</span>
  );

export const stars = (n: unknown) => (typeof n === "number" ? "★".repeat(n) : "—");

const LOCATION_FIELDS = (section = "Location"): FieldDef[] => [
  { name: "address", label: "Address", type: "text", section, wide: true },
  { name: "latitude", label: "Latitude", type: "float", section, placeholder: "e.g. 52.3600" },
  { name: "longitude", label: "Longitude", type: "float", section, placeholder: "e.g. 4.8852" },
];

const DEMO_FIELD: FieldDef = {
  name: "is_demo", label: "Demonstration data", type: "bool", section: "Status",
  hint: "Fictional sample record; shown with a DEMO badge and never presented as real.",
};

// ------------------------------------------------------------------ resources
export const RESOURCES: Record<ResourceKey, ResourceConfig> = {
  countries: {
    key: "countries", title: "Countries", singular: "Country", icon: MapPin, basePath: "/inventory/countries", hasImages: true,
    description: "Destination countries offered by YANA DMC. Add new ones at any time; no code changes needed.",
    searchPlaceholder: "Search country, ISO code or region",
    subtitle: (i) => [i.iso_code, i.region].filter(Boolean).join(" · "),
    columns: [
      { header: "Code", render: (i) => <span className="font-mono text-xs">{String(i.iso_code)}</span>, className: "hidden sm:table-cell" },
      { header: "Region", render: (i) => (i.region as string) ?? "—", className: "hidden md:table-cell" },
      { header: "Cities", render: (i) => String(i.city_count ?? 0), className: "text-right tabular-nums" },
    ],
    filters: [],
    fields: [
      { name: "name", label: "Country name", type: "text", section: "Country", required: true },
      { name: "iso_code", label: "ISO code", type: "text", section: "Country", required: true, placeholder: "e.g. NL", hint: "Two-letter country code" },
      { name: "region", label: "Region", type: "text", section: "Country", placeholder: "e.g. Western Europe" },
      { name: "sort_order", label: "Display order", type: "int", section: "Country", hint: "Lower numbers appear first" },
      { name: "description", label: "Description", type: "textarea", section: "Country", wide: true },
    ],
  },
  cities: {
    key: "cities", title: "Cities", singular: "City", icon: Building2, basePath: "/inventory/cities", hasImages: true,
    description: "Cities and towns within each country, with location and recommended stay.",
    searchPlaceholder: "Search city",
    subtitle: (i) => (i.country as { name: string } | undefined)?.name ?? "",
    columns: [
      { header: "Country", render: (i) => i.country?.name ?? "—", className: "hidden sm:table-cell" },
      {
        header: "Recommended stay",
        render: (i) =>
          i.recommended_nights_min != null || i.recommended_nights_max != null
            ? `${i.recommended_nights_min ?? "?"}–${i.recommended_nights_max ?? "?"} nights`
            : "—",
        className: "hidden md:table-cell",
      },
    ],
    filters: [{ param: "country_id", label: "All countries", ref: "countries" }],
    fields: [
      { name: "country_id", label: "Country", type: "reference", ref: "countries", section: "City", required: true },
      { name: "name", label: "City name", type: "text", section: "City", required: true },
      { name: "recommended_nights_min", label: "Recommended nights (min)", type: "int", section: "City" },
      { name: "recommended_nights_max", label: "Recommended nights (max)", type: "int", section: "City" },
      { name: "description", label: "Description", type: "textarea", section: "City", wide: true },
      { name: "latitude", label: "Latitude", type: "float", section: "Location", placeholder: "e.g. 52.3676", hint: "Used for routes and maps" },
      { name: "longitude", label: "Longitude", type: "float", section: "Location", placeholder: "e.g. 4.9041" },
    ],
  },
  attractions: {
    key: "attractions", title: "Sightseeing", singular: "Attraction", icon: Landmark, basePath: "/inventory/sightseeing", hasImages: true,
    description: "Attractions and experiences, tagged by interest so the itinerary engine can match customer preferences.",
    searchPlaceholder: "Search attraction or city",
    subtitle: (i) => [humanize(String(i.category)), i.city?.name].filter(Boolean).join(" · "),
    columns: [
      { header: "City", render: cityCell, className: "hidden sm:table-cell" },
      { header: "Category", render: (i) => humanize(String(i.category)), className: "hidden md:table-cell" },
      {
        header: "Duration",
        render: (i) => (i.recommended_duration_min ? `${Math.round(Number(i.recommended_duration_min) / 6) / 10} h` : "—"),
        className: "hidden lg:table-cell",
      },
      { header: "Ticket", render: (i) => (i.ticket_required ? priceCell(i.ticket_price, i.currency, i.price_is_verified) : "Free / none"), className: "hidden lg:table-cell" },
    ],
    filters: [
      { param: "country_id", label: "All countries", ref: "countries" },
      { param: "category", label: "All categories", vocab: "attraction_categories" },
      { param: "child_friendly", label: "Any age", staticOptions: [["true", "Suitable for children"]] },
    ],
    fields: [
      { name: "city_id", label: "City", type: "reference", ref: "cities", section: "Attraction", required: true },
      { name: "name", label: "Attraction name", type: "text", section: "Attraction", required: true },
      { name: "category", label: "Category", type: "select", vocab: "attraction_categories", section: "Attraction", required: true },
      { name: "setting", label: "Indoor / outdoor", type: "select", vocab: "attraction_settings", section: "Attraction" },
      { name: "description", label: "Description", type: "textarea", section: "Attraction", wide: true },
      { name: "interest_tags", label: "Matches interests", type: "multi", vocab: "interest_tags", section: "Matching", wide: true, hint: "Used to match customer travel interests" },
      { name: "child_friendly", label: "Suitable for children", type: "tristate", section: "Matching" },
      { name: "recommended_duration_min", label: "Recommended duration (minutes)", type: "int", section: "Visit" },
      { name: "opening_hours", label: "Opening hours", type: "text", section: "Visit", placeholder: "e.g. 09:00–17:00", wide: true },
      { name: "operating_days", label: "Open on", type: "multi", vocab: "weekdays", section: "Visit", wide: true },
      { name: "seasonal_info", label: "Seasonal information", type: "text", section: "Visit", wide: true, placeholder: "e.g. Closed Nov–Mar" },
      { name: "ticket_required", label: "Ticket required", type: "bool", section: "Tickets" },
      { name: "ticket_price", label: "Ticket price (per person)", type: "decimal", section: "Tickets" },
      { name: "currency", label: "Currency", type: "currency", section: "Tickets" },
      { name: "price_is_verified", label: "Price verified with supplier", type: "bool", section: "Tickets", hint: "Unverified prices are shown as estimates" },
      { name: "supplier_id", label: "Supplier", type: "reference", ref: "suppliers", section: "Tickets" },
      ...LOCATION_FIELDS(),
      DEMO_FIELD,
    ],
  },
  hotels: {
    key: "hotels", title: "Hotels", singular: "Hotel", icon: HotelIcon, basePath: "/inventory/hotels", hasImages: true,
    description: "Hotel inventory with room types and indicative seasonal rates. Availability is never assumed.",
    searchPlaceholder: "Search hotel or city",
    subtitle: (i) => [stars(i.star_rating), i.city?.name].filter((x) => x && x !== "—").join(" · "),
    columns: [
      { header: "City", render: cityCell, className: "hidden sm:table-cell" },
      { header: "Rating", render: (i) => <span className="text-brand-gold">{stars(i.star_rating)}</span> },
      { header: "Location", render: (i) => (i.location_type ? humanize(String(i.location_type)) : "—"), className: "hidden lg:table-cell" },
      { header: "Room types", render: (i) => String((i.room_types as unknown[] | undefined)?.length ?? 0), className: "hidden md:table-cell text-right tabular-nums" },
    ],
    filters: [
      { param: "country_id", label: "All countries", ref: "countries" },
      { param: "star_rating", label: "Any rating", staticOptions: [["5", "5★"], ["4", "4★"], ["3", "3★"], ["2", "2★"], ["1", "1★"]] },
    ],
    fields: [
      { name: "city_id", label: "City", type: "reference", ref: "cities", section: "Hotel", required: true },
      { name: "name", label: "Hotel name", type: "text", section: "Hotel", required: true },
      { name: "star_rating", label: "Star rating", type: "select", staticOptions: [["5", "5★"], ["4", "4★"], ["3", "3★"], ["2", "2★"], ["1", "1★"]], section: "Hotel" },
      { name: "location_type", label: "Location type", type: "select", vocab: "location_types", section: "Hotel" },
      { name: "style_tags", label: "Style", type: "multi", vocab: "hotel_styles", section: "Hotel", wide: true },
      { name: "description", label: "Description", type: "textarea", section: "Hotel", wide: true },
      { name: "breakfast_available", label: "Breakfast available", type: "tristate", section: "Facilities" },
      { name: "parking", label: "Parking", type: "tristate", section: "Facilities" },
      { name: "group_capacity_rooms", label: "Group capacity (rooms)", type: "int", section: "Facilities" },
      { name: "facilities", label: "Facilities", type: "multi", vocab: "hotel_facilities", section: "Facilities", wide: true },
      { name: "supplier_id", label: "Supplier", type: "reference", ref: "suppliers", section: "Contact" },
      { name: "contact_email", label: "Contact email", type: "email", section: "Contact" },
      { name: "contact_phone", label: "Contact phone", type: "text", section: "Contact" },
      ...LOCATION_FIELDS(),
      DEMO_FIELD,
    ],
  },
  restaurants: {
    key: "restaurants", title: "Restaurants", singular: "Restaurant", icon: UtensilsCrossed, basePath: "/inventory/restaurants", hasImages: true,
    description: "Restaurants with verified dietary options. Unknown is never treated as available.",
    searchPlaceholder: "Search restaurant, cuisine or city",
    subtitle: (i) => [i.cuisine as string, i.city?.name].filter(Boolean).join(" · "),
    columns: [
      { header: "City", render: cityCell, className: "hidden sm:table-cell" },
      { header: "Cuisine", render: (i) => (i.cuisine as string) ?? "—", className: "hidden md:table-cell" },
      {
        header: "Dietary (verified)",
        render: (i) => {
          const tags = (["vegetarian", "jain", "halal", "vegan"] as const).filter((k) => i[k] === true);
          return tags.length ? tags.map(humanize).join(", ") : <span className="text-muted-foreground">Not verified</span>;
        },
      },
      { header: "Price", render: (i) => (i.price_range as string) ?? "—", className: "hidden lg:table-cell" },
    ],
    filters: [
      { param: "country_id", label: "All countries", ref: "countries" },
      { param: "diet", label: "Any dietary option", staticOptions: [["vegetarian", "Vegetarian"], ["jain", "Jain"], ["halal", "Halal"], ["vegan", "Vegan"]] },
    ],
    fields: [
      { name: "city_id", label: "City", type: "reference", ref: "cities", section: "Restaurant", required: true },
      { name: "name", label: "Restaurant name", type: "text", section: "Restaurant", required: true },
      { name: "cuisine", label: "Cuisine", type: "text", section: "Restaurant", placeholder: "e.g. North Indian" },
      { name: "price_range", label: "Price range", type: "select", vocab: "price_ranges", section: "Restaurant" },
      { name: "description", label: "Description", type: "textarea", section: "Restaurant", wide: true },
      { name: "vegetarian", label: "Indian vegetarian / vegetarian", type: "tristate", section: "Dietary (only mark Yes when verified)" },
      { name: "jain", label: "Jain", type: "tristate", section: "Dietary (only mark Yes when verified)" },
      { name: "halal", label: "Halal", type: "tristate", section: "Dietary (only mark Yes when verified)" },
      { name: "vegan", label: "Vegan", type: "tristate", section: "Dietary (only mark Yes when verified)" },
      { name: "non_vegetarian", label: "Non-vegetarian", type: "tristate", section: "Dietary (only mark Yes when verified)" },
      { name: "group_capacity", label: "Group capacity (guests)", type: "int", section: "Groups & pricing" },
      { name: "avg_price_per_person", label: "Average price per person", type: "decimal", section: "Groups & pricing" },
      { name: "currency", label: "Currency", type: "currency", section: "Groups & pricing" },
      { name: "price_is_verified", label: "Price verified with supplier", type: "bool", section: "Groups & pricing" },
      { name: "opening_hours", label: "Opening hours", type: "text", section: "Groups & pricing", wide: true },
      { name: "supplier_id", label: "Supplier", type: "reference", ref: "suppliers", section: "Contact" },
      { name: "contact_email", label: "Contact email", type: "email", section: "Contact" },
      { name: "contact_phone", label: "Contact phone", type: "text", section: "Contact" },
      ...LOCATION_FIELDS(),
      DEMO_FIELD,
    ],
  },
  vehicles: {
    key: "vehicles", title: "Transportation", singular: "Vehicle", icon: Bus, basePath: "/inventory/transportation", hasImages: true,
    description: "Coaches, minibuses and cars from your transport suppliers, with indicative daily and per-km costs.",
    searchPlaceholder: "Search vehicle",
    subtitle: (i) => `${(i.category as { name: string } | undefined)?.name ?? ""} · ${i.passenger_capacity} passengers`,
    columns: [
      { header: "Category", render: (i) => (i.category as { name: string } | undefined)?.name ?? "—", className: "hidden sm:table-cell" },
      { header: "Seats", render: (i) => String(i.passenger_capacity), className: "text-right tabular-nums" },
      { header: "Supplier", render: (i) => i.supplier?.name ?? "—", className: "hidden md:table-cell" },
      { header: "Per day", render: (i) => priceCell(i.price_per_day, i.currency, i.price_is_verified), className: "hidden lg:table-cell" },
    ],
    filters: [
      { param: "category_id", label: "All categories", ref: "vehicleCategories" },
      { param: "supplier_id", label: "All suppliers", ref: "suppliers" },
    ],
    fields: [
      { name: "category_id", label: "Vehicle category", type: "reference", ref: "vehicleCategories", section: "Vehicle", required: true },
      { name: "name", label: "Vehicle name / description", type: "text", section: "Vehicle", required: true, placeholder: "e.g. 49-seat Setra touring coach" },
      { name: "passenger_capacity", label: "Passenger capacity", type: "int", section: "Vehicle", required: true },
      { name: "luggage_capacity", label: "Luggage capacity (pieces)", type: "int", section: "Vehicle" },
      { name: "supplier_id", label: "Supplier", type: "reference", ref: "suppliers", section: "Vehicle" },
      { name: "service_types", label: "Services", type: "multi", vocab: "service_types", section: "Operations", wide: true },
      {
        name: "operating_country_ids", label: "Operating countries", type: "multiref", ref: "countries", section: "Operations", wide: true,
        get: (i) => ((i.operating_countries as { id: number }[] | undefined) ?? []).map((c) => c.id),
      },
      { name: "availability_notes", label: "Availability notes", type: "textarea", section: "Operations", wide: true },
      { name: "price_per_day", label: "Price per day", type: "decimal", section: "Costs" },
      { name: "price_per_km", label: "Price per km", type: "decimal", section: "Costs" },
      { name: "driver_cost_per_day", label: "Driver cost per day", type: "decimal", section: "Costs" },
      { name: "currency", label: "Currency", type: "currency", section: "Costs" },
      { name: "additional_costs", label: "Additional costs", type: "textarea", section: "Costs", wide: true, hint: "Tolls, parking, driver accommodation…" },
      { name: "price_is_verified", label: "Prices verified with supplier", type: "bool", section: "Costs" },
      DEMO_FIELD,
    ],
  },
  suppliers: {
    key: "suppliers", title: "Suppliers", singular: "Supplier", icon: Truck, basePath: "/suppliers", hasImages: false,
    description: "Hotels, coach companies, restaurants, guides and other ground-service partners.",
    searchPlaceholder: "Search supplier, contact or email",
    subtitle: (i) => [humanize(String(i.supplier_type)), i.country?.name].filter(Boolean).join(" · "),
    columns: [
      { header: "Type", render: (i) => humanize(String(i.supplier_type)) },
      { header: "Contact", render: (i) => (i.contact_name as string) ?? (i.email as string) ?? "—", className: "hidden md:table-cell" },
      { header: "Country", render: (i) => i.country?.name ?? "—", className: "hidden lg:table-cell" },
    ],
    filters: [
      { param: "supplier_type", label: "All types", vocab: "supplier_types" },
      { param: "country_id", label: "All countries", ref: "countries" },
    ],
    fields: [
      { name: "name", label: "Supplier name", type: "text", section: "Supplier", required: true },
      { name: "supplier_type", label: "Type", type: "select", vocab: "supplier_types", section: "Supplier", required: true },
      { name: "country_id", label: "Country", type: "reference", ref: "countries", section: "Supplier" },
      { name: "address", label: "Address", type: "text", section: "Supplier", wide: true },
      { name: "contact_name", label: "Contact person", type: "text", section: "Contact" },
      { name: "email", label: "Email", type: "email", section: "Contact" },
      { name: "phone", label: "Phone", type: "text", section: "Contact" },
      { name: "notes", label: "Internal notes", type: "textarea", section: "Contact", wide: true },
      DEMO_FIELD,
    ],
  },
};

/** URL path segment → resource (e.g. /inventory/sightseeing → attractions). */
export const RESOURCE_BY_SEGMENT: Record<string, ResourceKey> = {
  countries: "countries",
  cities: "cities",
  sightseeing: "attractions",
  hotels: "hotels",
  restaurants: "restaurants",
  transportation: "vehicles",
};
