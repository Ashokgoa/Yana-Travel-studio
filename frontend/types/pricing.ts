export type PricingCategory = "hotel" | "transport" | "transfer" | "sightseeing" | "guide" | "meal" | "other";
export type PricingBasis = "per_person" | "per_room" | "per_day" | "per_vehicle" | "per_km" | "group";

export const CATEGORY_LABELS: Record<PricingCategory, string> = {
  hotel: "Hotels", transport: "Transport", transfer: "Transfers", sightseeing: "Sightseeing", guide: "Guides", meal: "Meals", other: "Other",
};
export const CATEGORIES = Object.keys(CATEGORY_LABELS) as PricingCategory[];
export const BASIS_LABELS: Record<PricingBasis, string> = {
  per_person: "per person", per_room: "per room per night", per_day: "per day", per_vehicle: "per vehicle", per_km: "per km", group: "per group",
};

export type PricingLine = {
  key: string;
  manual_id: number | null;
  category: PricingCategory;
  basis: PricingBasis;
  description: string;
  unit_cost: string | null;
  quantity: string;
  total: string | null;
  is_estimate: boolean;
  included: boolean;
  is_overridden: boolean;
  auto_unit_cost: string | null;
};

export type StayRate = { key: string; label: string; nights: number; double_rate: string | null; single_rate: string | null; single_is_estimate: boolean; is_overridden: boolean };
export type Prices = { currency: string; adult_twin: string | null; single_supplement: string | null; child_with_bed: string | null; child_without_bed: string | null };

export type PricingView = {
  version_number: number;
  version_label: string;
  currency: string;
  margins: Record<PricingCategory, string>;
  discount_pct: string;
  adjustment_per_person: string;
  rounding: string;
  child_bed_pct: string;
  adults: number;
  children_with_bed: number;
  children_without_bed: number;
  singles: number;
  travellers_from_enquiry: { adults: number; children: number; singles: number };
  display_currency: string | null;
  exchange_rate: string | null;
  pdf_currency: "base" | "display" | "both";
  notes: string | null;
  lines: PricingLine[];
  stays: StayRate[];
  categories: { category: PricingCategory; label: string; cost: string; margin_pct: string; per_person_cost: string; per_person_selling: string }[];
  prices: Prices;
  display_prices: Prices | null;
  adult_twin_cost: string;
  total_cost: string;
  revenue: string;
  profit: string;
  margin_on_revenue_pct: string | null;
  budget_per_person: string | null;
  warnings: string[];
  margins_reviewed: boolean;
};

export type PricingUpdate = Partial<{
  margins: Partial<Record<PricingCategory, string>>;
  discount_pct: string;
  adjustment_per_person: string;
  rounding: string;
  child_bed_pct: string;
  adults: number;
  children_with_bed: number;
  children_without_bed: number;
  singles: number;
  display_currency: string | null;
  exchange_rate: string | null;
  pdf_currency: "base" | "display" | "both";
  notes: string | null;
}>;

export type ManualLine = { category: PricingCategory; basis: PricingBasis; description: string; unit_cost: string | null; quantity: string; is_estimate: boolean };

export type PricingDefaults = {
  margins: Record<PricingCategory, string>;
  rounding: string;
  child_bed_pct: string;
  display_currency: string | null;
  exchange_rate: string | null;
  margins_reviewed: boolean;
};
