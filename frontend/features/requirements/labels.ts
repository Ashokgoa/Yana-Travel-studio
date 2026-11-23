import { humanize } from "@/features/inventory/resource-config";
import type { Choice } from "@/components/common/choice-controls";
import type { Preference } from "@/types/requirements";

const LABELS: Record<string, string> = {
  "3_star": "3★",
  "4_star": "4★",
  "5_star": "5★",
  city_centre: "City centre",
  anywhere: "No preference",
  indian_vegetarian: "Indian vegetarian",
  indian_jain: "Indian Jain",
  indian_non_vegetarian: "Indian non-vegetarian",
  mixed: "Mixed cuisine",
  private_coach: "Private coach",
  luxury_coach: "Luxury coach",
  mini_bus: "Mini bus",
  private_car: "Private car",
  some: "Some flexibility",
  strict: "Strict",
  flexible: "Flexible",
};

export const label = (code: string) => LABELS[code] ?? humanize(code);
export const choices = (codes: string[] | undefined): Choice[] => (codes ?? []).map((c) => ({ value: c, label: label(c) }));

export const PREFERENCE_META: Record<Preference, { label: string; className: string; hint: string }> = {
  mandatory: { label: "Must visit", className: "bg-emerald-50 text-emerald-800 ring-emerald-600/25", hint: "Never dropped; the planner is warned if it doesn't fit" },
  preferred: { label: "Preferred", className: "bg-sky-50 text-sky-800 ring-sky-600/25", hint: "Included when time allows" },
  optional: { label: "Optional", className: "bg-zinc-100 text-zinc-700 ring-zinc-500/20", hint: "Only if it fits naturally" },
  avoid: { label: "Avoid", className: "bg-rose-50 text-rose-800 ring-rose-600/25", hint: "Never included" },
};

export const STEPS = [
  { n: 1, title: "Travellers", description: "Who is travelling" },
  { n: 2, title: "Travel", description: "Dates, airports and route ends" },
  { n: 3, title: "Destinations", description: "Countries and cities: must-visit, optional, avoid" },
  { n: 4, title: "Interests", description: "What the customer enjoys" },
  { n: 5, title: "Hotels", description: "Category, location and rooms" },
  { n: 6, title: "Food", description: "Dietary preferences and meals" },
  { n: 7, title: "Transport", description: "Vehicles and transfers" },
  { n: 8, title: "Budget", description: "Amount and flexibility" },
  { n: 9, title: "Notes", description: "Anything else" },
  { n: 10, title: "Review", description: "Check and finish" },
] as const;
