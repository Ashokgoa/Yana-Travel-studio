export type ProposalTemplate = "classic" | "premium" | "explorer";
export type ProposalBranding = "agent" | "yana" | "both";
export type SectionKey = "cover" | "highlights" | "route_map" | "days" | "hotels" | "summary" | "price" | "inclusions" | "terms" | "closing";

export type ProposalSettings = {
  template: ProposalTemplate;
  branding: ProposalBranding;
  sections: { key: SectionKey; enabled: boolean }[];
  title: string | null;
  intro: string | null;
  closing: string | null;
  inclusions: string[] | null;
  exclusions: string[] | null;
  terms: string | null;
  hotel_names_in_days: boolean;
  price_per_person: string | null;
  price_currency: string;
  price_note: string | null;
  /** Day number (as text) -> media id; 0 hides the photo. */
  day_images: Record<string, number>;
  /** Day number (as text) -> PDF wording; null fields = automatic. Use **bold**. */
  day_texts: Record<string, DayText>;
  cover_image: number | null;
  primary_color: string | null;
  accent_color: string | null;
};

export type DayText = { heading: string | null; subtitle: string | null; bullets: string[] | null; meals: string | null; note: string | null };
export type AutoDayText = { day_number: number; heading: string; subtitle: string; bullets: string[]; meals: string; note: string };

export type ImageChoice = { media_id: number; label: string; kind: "attraction" | "hotel" | "city"; url: string };

export type ProposalOptions = {
  templates: { key: ProposalTemplate; label: string; description: string }[];
  sections: { key: SectionKey; label: string }[];
  day_images: { day_number: number; title: string; choices: ImageChoice[] }[];
  /** Internal only: never shown in the PDF. */
  internal_estimate_per_person: string | null;
  currency: string;
  defaults: { title: string; intro: string; closing: string; inclusions: string[]; exclusions: string[]; terms: string; days: AutoDayText[] };
  version_number: number;
  version_label: string;
  version_is_locked: boolean;
  /** Selling price from the pricing sheet (never costs). */
  pricing: { status: "none" | "ok" | "incomplete"; text: string | null };
};

export type ProposalExport = {
  id: number;
  itinerary_id: number;
  version_number: number;
  filename: string;
  template: ProposalTemplate;
  branding: ProposalBranding;
  size_bytes: number;
  created_at: string;
  created_by_name: string | null;
};

export type BrandingSettings = {
  company_name: string;
  tagline: string | null;
  contact_line: string | null;
  logo_media_id: number | null;
  primary_color: string;
  accent_color: string;
  default_closing: string;
  default_exclusions: string[];
  default_terms: string;
  terms_reviewed: boolean;
};
