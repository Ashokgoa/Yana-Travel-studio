import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";
import { DetailItem } from "@/components/common/states";
import { label, PREFERENCE_META } from "@/features/requirements/labels";
import { formatDate, formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Requirement } from "@/types/requirements";

const list = (codes: string[]) => (codes.length ? codes.map(label).join(", ") : null);

export function ReadinessList({ req }: { req: Requirement }) {
  return (
    <div className="space-y-3 text-sm">
      {req.missing.length === 0 ? (
        <p className="flex items-center gap-2 font-medium text-emerald-700"><CheckCircle2 className="size-4" aria-hidden /> Ready for itinerary generation</p>
      ) : (
        <div>
          <p className="mb-1 font-medium">Still needed</p>
          <ul className="space-y-1">
            {req.missing.map((m) => <li key={m} className="flex items-center gap-2 text-muted-foreground"><CircleDashed className="size-3.5 shrink-0" aria-hidden />{m}</li>)}
          </ul>
        </div>
      )}
      {req.warnings.length > 0 && (
        <div>
          <p className="mb-1 font-medium text-amber-800">Check</p>
          <ul className="space-y-1.5">
            {req.warnings.map((w) => <li key={w} className="flex gap-2 text-amber-800"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />{w}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

export function PreferencePill({ preference }: { preference: keyof typeof PREFERENCE_META }) {
  const m = PREFERENCE_META[preference];
  return <span className={cn("rounded-full px-2 py-0.5 font-sans text-[11px] font-medium whitespace-nowrap ring-1 ring-inset", m.className)}>{m.label}</span>;
}

export function RequirementsSummary({ req }: { req: Requirement }) {
  const rooms = req.rooms.map((r) => `${r.count}× ${label(r.type)}`).join(", ");
  const budget = req.budget_per_person
    ? `${formatMoney(req.budget_per_person, req.currency)} per person`
    : req.budget_total
      ? `${formatMoney(req.budget_total, req.currency)} group total`
      : null;
  return (
    <dl className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <DetailItem label="Dates">{req.arrival_date ? `${formatDate(req.arrival_date)} – ${formatDate(req.departure_date)}` : null}</DetailItem>
      <DetailItem label="Duration">{req.total_days ? `${req.total_days} days / ${req.total_nights} nights` : null}</DetailItem>
      <DetailItem label="Travellers">
        {`${req.adults} adult${req.adults === 1 ? "" : "s"}`}
        {req.children ? `, ${req.children} child${req.children === 1 ? "" : "ren"} (ages ${req.children_ages.join(", ")})` : ""}
        {req.travel_type ? ` · ${req.travel_type}` : ""}
      </DetailItem>
      <DetailItem label="Arrive / depart">{req.arrival_airport || req.departure_airport ? `${req.arrival_airport ?? "?"} → ${req.departure_airport ?? "?"}` : null}</DetailItem>
      <DetailItem label="Interests">{list(req.interests)}{req.travel_pace ? ` · ${label(req.travel_pace)} pace` : ""}</DetailItem>
      <DetailItem label="Hotels">
        {[list(req.hotel_categories), list(req.hotel_locations), req.breakfast_required ? "breakfast" : null, rooms || null].filter(Boolean).join(" · ") || null}
      </DetailItem>
      <DetailItem label="Food">{[list(req.food_preferences), req.meals.length ? `meals: ${req.meals.join(", ")}` : null].filter(Boolean).join(" · ") || null}</DetailItem>
      <DetailItem label="Transport">
        {[list(req.transport_modes), req.passenger_capacity ? `${req.passenger_capacity} seats` : null, req.airport_transfers ? "airport transfers" : null].filter(Boolean).join(" · ") || null}
      </DetailItem>
      <DetailItem label="Budget">
        {budget}
        {budget && req.budget_flexibility ? ` · ${label(req.budget_flexibility)}` : ""}
        {budget && req.travel_class ? ` · ${label(req.travel_class)}` : ""}
      </DetailItem>
      <div className="sm:col-span-2 lg:col-span-3">
        <DetailItem label="Destinations (in preferred order)">
          {req.destinations.length ? (
            <span className="flex flex-wrap gap-2">
              {req.destinations.map((d) => (
                <span key={d.id} className="inline-flex items-center gap-1.5 rounded-lg border bg-card px-2.5 py-1">
                  {d.city ? `${d.city.name}, ${d.country.iso_code}` : d.country.name}
                  {d.min_nights ? <span className="text-xs text-muted-foreground">≥{d.min_nights}N</span> : null}
                  <PreferencePill preference={d.preference} />
                </span>
              ))}
            </span>
          ) : null}
        </DetailItem>
      </div>
      {req.additional_requirements && (
        <div className="sm:col-span-2 lg:col-span-3"><DetailItem label="Additional requirements"><span className="whitespace-pre-line">{req.additional_requirements}</span></DetailItem></div>
      )}
      {req.internal_notes && (
        <div className="sm:col-span-2 lg:col-span-3"><DetailItem label="Internal notes (staff only)"><span className="whitespace-pre-line">{req.internal_notes}</span></DetailItem></div>
      )}
    </dl>
  );
}
