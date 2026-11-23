"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, CalendarRange, Minus, Plus, Trash2, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChipGroup, Segmented, Toggle } from "@/components/common/choice-controls";
import { controlClass, FormField, NativeSelect } from "@/components/common/form-controls";
import { CURRENCIES } from "@/features/inventory/resource-config";
import { choices, label, PREFERENCE_META } from "@/features/requirements/labels";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { inventoryApi } from "@/services/inventory";
import type { EnquiryDetail } from "@/types/crm";
import type { Preference, RequirementInput, RequirementOptions } from "@/types/requirements";

export type StepProps = {
  value: RequirementInput;
  set: (patch: Partial<RequirementInput>) => void;
  options: RequirementOptions;
  enquiry: EnquiryDetail;
};

const num = (v: number | null | undefined) => (v === null || v === undefined ? "" : String(v));
const toInt = (s: string) => (s.trim() === "" || !/^\d+$/.test(s.trim()) ? null : Number(s));
const ROOM_SLEEPS: Record<string, number> = { single: 1, double: 2, twin: 2, triple: 3, family: 4, suite: 2 };

function useCountriesAndCities() {
  const countries = useQuery({ queryKey: ["inventory", "countries", "list", { active: true, page_size: 100 }], queryFn: () => inventoryApi.list("countries", { active: true, page_size: 100 }) });
  const cities = useQuery({ queryKey: ["inventory", "cities", "list", { active: true, page_size: 100 }], queryFn: () => inventoryApi.list("cities", { active: true, page_size: 100 }) });
  return { countries: countries.data?.items ?? [], cities: cities.data?.items ?? [], loading: countries.isPending || cities.isPending };
}

function Counter({ id, value, onChange, min = 0, max = 500 }: { id: string; value: number; onChange: (v: number) => void; min?: number; max?: number }) {
  return (
    <div className="inline-flex items-center rounded-lg border">
      <Button type="button" variant="ghost" size="icon" aria-label="Decrease" disabled={value <= min} onClick={() => onChange(value - 1)}><Minus /></Button>
      <input id={id} inputMode="numeric" className="h-9 w-14 border-x bg-transparent text-center text-sm tabular-nums outline-none" value={value}
        onChange={(e) => { const n = toInt(e.target.value); if (n !== null) onChange(Math.min(max, Math.max(min, n))); }} />
      <Button type="button" variant="ghost" size="icon" aria-label="Increase" disabled={value >= max} onClick={() => onChange(value + 1)}><Plus /></Button>
    </div>
  );
}

// ------------------------------------------------------------------ 1 Travellers
export function StepTravellers({ value, set, enquiry }: StepProps) {
  const setChildren = (n: number) => set({ children: n, children_ages: Array.from({ length: n }, (_, i) => value.children_ages[i] ?? 0) });
  return (
    <div className="space-y-6">
      <div className="grid gap-4 rounded-xl border bg-muted/30 p-4 text-sm sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Travel agent</p>
          <Link href={`/crm/agents/${enquiry.travel_agent.id}`} className="font-medium text-brand-teal hover:underline">{enquiry.travel_agent.company_name}</Link>
        </div>
        <div>
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Customer</p>
          <Link href={`/crm/customers/${enquiry.customer.id}`} className="font-medium text-brand-teal hover:underline">{enquiry.customer.name}</Link>
          <p className="text-xs text-muted-foreground">Contact details are kept on the customer record.</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-8">
        <FormField label="Adults" htmlFor="rq-adults"><Counter id="rq-adults" value={value.adults} onChange={(adults) => set({ adults })} /></FormField>
        <FormField label="Children (0–17)" htmlFor="rq-children"><Counter id="rq-children" value={value.children} onChange={setChildren} max={50} /></FormField>
      </div>
      {value.children > 0 && (
        <fieldset>
          <legend className="mb-2 text-sm font-medium">Children&apos;s ages</legend>
          <div className="flex flex-wrap gap-3">
            {value.children_ages.map((age, i) => (
              <label key={i} className="w-24 text-xs text-muted-foreground">
                Child {i + 1}
                <NativeSelect aria-label={`Age of child ${i + 1}`} value={String(age)} onChange={(e) => set({ children_ages: value.children_ages.map((a, j) => (j === i ? Number(e.target.value) : a)) })}>
                  {Array.from({ length: 18 }, (_, a) => <option key={a} value={a}>{a === 0 ? "Under 1" : a}</option>)}
                </NativeSelect>
              </label>
            ))}
          </div>
        </fieldset>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ 2 Travel
export function StepTravel({ value, set }: StepProps) {
  const { countries } = useCountriesAndCities();
  const nights = value.arrival_date && value.departure_date ? Math.round((Date.parse(value.departure_date) - Date.parse(value.arrival_date)) / 86_400_000) : null;
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <FormField label="Arrival date" htmlFor="rq-arr" required>
        <input id="rq-arr" type="date" className={controlClass} value={value.arrival_date ?? ""} onChange={(e) => set({ arrival_date: e.target.value || null })} />
      </FormField>
      <FormField label="Departure date" htmlFor="rq-dep" required>
        <input id="rq-dep" type="date" min={value.arrival_date ?? undefined} className={controlClass} value={value.departure_date ?? ""} onChange={(e) => set({ departure_date: e.target.value || null })} />
      </FormField>
      <p className={cn("flex items-center gap-2 text-sm sm:col-span-2", nights !== null && nights < 0 ? "text-destructive" : "text-muted-foreground")}>
        <CalendarRange className="size-4 text-brand-teal" aria-hidden />
        {nights === null ? "Choose both dates to see the trip length." : nights < 0 ? "Departure is before arrival." : `${nights + 1} days / ${nights} nights`}
      </p>
      <FormField label="Arrival airport / city" htmlFor="rq-aap" required hint="e.g. Amsterdam Schiphol (AMS)">
        <input id="rq-aap" className={controlClass} value={value.arrival_airport ?? ""} onChange={(e) => set({ arrival_airport: e.target.value })} />
      </FormField>
      <FormField label="Departure airport / city" htmlFor="rq-dap" required hint="e.g. Zurich (ZRH)">
        <input id="rq-dap" className={controlClass} value={value.departure_airport ?? ""} onChange={(e) => set({ departure_airport: e.target.value })} />
      </FormField>
      <FormField label="Preferred starting country" htmlFor="rq-sc">
        <NativeSelect id="rq-sc" value={num(value.start_country_id)} onChange={(e) => set({ start_country_id: toInt(e.target.value) })}>
          <option value="">No preference</option>
          {countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </NativeSelect>
      </FormField>
      <FormField label="Preferred ending country" htmlFor="rq-ec">
        <NativeSelect id="rq-ec" value={num(value.end_country_id)} onChange={(e) => set({ end_country_id: toInt(e.target.value) })}>
          <option value="">No preference</option>
          {countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </NativeSelect>
      </FormField>
      <FormField label="Travel type" htmlFor="rq-tt" hint="FIT = individual travellers · GIT = group tour">
        <Segmented id="rq-tt" label="Travel type" value={value.travel_type ?? ""} onChange={(v) => set({ travel_type: (v || null) as RequirementInput["travel_type"] })}
          options={[{ value: "FIT", label: "FIT (individual)" }, { value: "GIT", label: "GIT (group)" }, { value: "", label: "Not set" }]} />
      </FormField>
      {value.travel_type === "GIT" && (
        <FormField label="Group size" htmlFor="rq-gs">
          <input id="rq-gs" inputMode="numeric" className={controlClass} value={num(value.group_size)} onChange={(e) => set({ group_size: toInt(e.target.value) })} />
        </FormField>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ 3 Destinations
export function StepDestinations({ value, set, options }: StepProps) {
  const { countries, cities, loading } = useCountriesAndCities();
  const [countryId, setCountryId] = useState("");
  const [cityId, setCityId] = useState("");
  const [pref, setPref] = useState<Preference>("mandatory");
  const countryName = (id: number) => countries.find((c) => c.id === id)?.name ?? `#${id}`;
  const cityName = (id: number | null) => (id ? cities.find((c) => c.id === id)?.name ?? `#${id}` : null);
  const citiesOf = useMemo(() => cities.filter((c) => c.country?.id === Number(countryId)), [cities, countryId]);
  const exists = value.destinations.some((d) => d.country_id === Number(countryId) && (d.city_id ?? null) === (cityId ? Number(cityId) : null));
  const list = value.destinations;
  const update = (i: number, patch: Partial<(typeof list)[number]>) => set({ destinations: list.map((d, j) => (j === i ? { ...d, ...patch } : d)) });
  const move = (i: number, delta: number) => { const next = [...list]; const [x] = next.splice(i, 1); next.splice(i + delta, 0, x); set({ destinations: next }); };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-muted/30 p-4">
        <p className="mb-3 text-sm font-medium">Add a destination</p>
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <NativeSelect aria-label="Country" value={countryId} onChange={(e) => { setCountryId(e.target.value); setCityId(""); }} disabled={loading}>
            <option value="">{loading ? "Loading…" : "Select country"}</option>
            {countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </NativeSelect>
          <NativeSelect aria-label="City (optional)" value={cityId} onChange={(e) => setCityId(e.target.value)} disabled={!countryId || pref === "avoid"}>
            <option value="">{pref === "avoid" ? "Whole country" : "Any city (whole country)"}</option>
            {citiesOf.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </NativeSelect>
          <Button type="button" disabled={!countryId || exists}
            onClick={() => { set({ destinations: [...list, { country_id: Number(countryId), city_id: cityId && pref !== "avoid" ? Number(cityId) : null, preference: pref, min_nights: null }] }); setCityId(""); }}>
            <Plus aria-hidden /> Add
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Segmented label="Preference" value={pref} onChange={(v) => setPref(v as Preference)}
            options={options.preferences.map((p) => ({ value: p, label: PREFERENCE_META[p].label }))} />
          <span className="text-xs text-muted-foreground">{PREFERENCE_META[pref].hint}</span>
        </div>
        {exists && <p className="mt-2 text-xs text-amber-700">Already in the list.</p>}
      </div>

      {list.length === 0 ? (
        <p className="text-sm text-muted-foreground">No destinations yet. Add the countries (and any specific cities) the customer wants, including places to avoid.</p>
      ) : (
        <ol className="space-y-2" aria-label="Destinations in preferred order">
          {list.map((d, i) => (
            <li key={`${d.country_id}-${d.city_id}`} className="flex flex-wrap items-center gap-3 rounded-xl border bg-card p-3">
              <span className="w-6 text-center text-sm font-semibold text-muted-foreground tabular-nums">{i + 1}</span>
              <div className="min-w-40 flex-1">
                <p className="font-medium">{cityName(d.city_id) ?? countryName(d.country_id)}</p>
                <p className="text-xs text-muted-foreground">{d.city_id ? countryName(d.country_id) : "Whole country"}</p>
              </div>
              <Segmented size="sm" label={`Preference for ${cityName(d.city_id) ?? countryName(d.country_id)}`} value={d.preference}
                onChange={(v) => update(i, { preference: v as Preference, min_nights: v === "avoid" ? null : d.min_nights })}
                options={options.preferences.map((p) => ({ value: p, label: PREFERENCE_META[p].label }))} />
              {d.preference !== "avoid" && (
                <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  Min nights
                  <input inputMode="numeric" className={cn(controlClass, "h-8 w-14 px-2")} value={num(d.min_nights)} onChange={(e) => update(i, { min_nights: toInt(e.target.value) })} />
                </label>
              )}
              <div className="flex gap-0.5">
                <Button type="button" variant="ghost" size="icon" aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp /></Button>
                <Button type="button" variant="ghost" size="icon" aria-label="Move down" disabled={i === list.length - 1} onClick={() => move(i, 1)}><ArrowDown /></Button>
                <Button type="button" variant="ghost" size="icon" aria-label="Remove destination" onClick={() => set({ destinations: list.filter((_, j) => j !== i) })}><Trash2 /></Button>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ 4 Interests
export function StepInterests({ value, set, options }: StepProps) {
  return (
    <div className="space-y-6">
      <FormField label="Travel interests" htmlFor="rq-int" hint="Used to pick sightseeing that matches the customer.">
        <ChipGroup id="rq-int" label="Travel interests" options={choices(options.interests)} value={value.interests} onChange={(interests) => set({ interests })} />
      </FormField>
      <FormField label="Travel pace" htmlFor="rq-pace">
        <Segmented id="rq-pace" label="Travel pace" value={value.travel_pace ?? ""} onChange={(v) => set({ travel_pace: v || null })}
          options={[...choices(options.travel_paces), { value: "", label: "Not set" }]} />
      </FormField>
    </div>
  );
}

// ------------------------------------------------------------------ 5 Hotels
export function StepHotels({ value, set, options }: StepProps) {
  const travellers = value.adults + value.children;
  const capacity = value.rooms.reduce((s, r) => s + (ROOM_SLEEPS[r.type] ?? 2) * r.count, 0);
  const rooms = value.rooms;
  return (
    <div className="space-y-6">
      <FormField label="Hotel category" htmlFor="rq-hc">
        <ChipGroup id="rq-hc" label="Hotel category" options={choices(options.hotel_categories)} value={value.hotel_categories} onChange={(hotel_categories) => set({ hotel_categories })} />
      </FormField>
      <FormField label="Location" htmlFor="rq-hl">
        <ChipGroup id="rq-hl" label="Hotel location" options={choices(options.hotel_locations)} value={value.hotel_locations} onChange={(hotel_locations) => set({ hotel_locations })} />
      </FormField>
      <Toggle id="rq-bf" checked={value.breakfast_required} onChange={(breakfast_required) => set({ breakfast_required })} label="Breakfast included" />
      <fieldset className="space-y-3">
        <legend className="text-sm font-medium">Rooms</legend>
        {rooms.map((r, i) => (
          <div key={i} className="flex flex-wrap items-center gap-3">
            <NativeSelect aria-label={`Room type ${i + 1}`} className="w-44" value={r.type} onChange={(e) => set({ rooms: rooms.map((x, j) => (j === i ? { ...x, type: e.target.value } : x)) })}>
              {options.room_types.map((t) => <option key={t} value={t}>{label(t)} (sleeps {ROOM_SLEEPS[t] ?? 2})</option>)}
            </NativeSelect>
            <Counter id={`rq-room-${i}`} value={r.count} min={1} max={200} onChange={(count) => set({ rooms: rooms.map((x, j) => (j === i ? { ...x, count } : x)) })} />
            <Button type="button" variant="ghost" size="icon" aria-label="Remove room line" onClick={() => set({ rooms: rooms.filter((_, j) => j !== i) })}><Trash2 /></Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" onClick={() => set({ rooms: [...rooms, { type: "double", count: 1 }] })}><Plus aria-hidden /> Add rooms</Button>
        {rooms.length > 0 && (
          <p className={cn("flex items-center gap-2 text-sm", capacity < travellers ? "text-amber-700" : "text-muted-foreground")}>
            <Users className="size-4" aria-hidden />
            {rooms.reduce((s, r) => s + r.count, 0)} rooms sleep {capacity} · {travellers} travellers
            {capacity < travellers && " (not enough beds)"}
          </p>
        )}
      </fieldset>
    </div>
  );
}

// ------------------------------------------------------------------ 6 Food
export function StepFood({ value, set, options }: StepProps) {
  const all = options.meals.every((m) => value.meals.includes(m));
  return (
    <div className="space-y-6">
      <FormField label="Food preferences" htmlFor="rq-food" hint="Restaurants are only suggested when the dietary option is verified in inventory.">
        <ChipGroup id="rq-food" label="Food preferences" options={choices(options.food_preferences)} value={value.food_preferences} onChange={(food_preferences) => set({ food_preferences })} />
      </FormField>
      <FormField label="Meals to include" htmlFor="rq-meals">
        <div className="flex flex-wrap items-center gap-3">
          <ChipGroup id="rq-meals" label="Meals" options={choices(options.meals)} value={value.meals} onChange={(meals) => set({ meals })} />
          <Button type="button" variant="ghost" size="sm" onClick={() => set({ meals: all ? [] : [...options.meals] })}>{all ? "Clear" : "All meals"}</Button>
        </div>
      </FormField>
    </div>
  );
}

// ------------------------------------------------------------------ 7 Transport
export function StepTransport({ value, set, options }: StepProps) {
  const travellers = value.adults + value.children;
  return (
    <div className="space-y-6">
      <FormField label="Transportation" htmlFor="rq-tr" hint="Choose several for mixed arrangements (e.g. coach plus train in Switzerland).">
        <ChipGroup id="rq-tr" label="Transportation" options={choices(options.transport_modes)} value={value.transport_modes} onChange={(transport_modes) => set({ transport_modes })} />
      </FormField>
      <div className="grid gap-5 sm:grid-cols-2">
        <FormField label="Passenger capacity needed" htmlFor="rq-cap" hint={`${travellers} travellers; add seats for a guide or tour leader if needed`}>
          <input id="rq-cap" inputMode="numeric" placeholder={String(travellers)} className={controlClass} value={num(value.passenger_capacity)} onChange={(e) => set({ passenger_capacity: toInt(e.target.value) })} />
        </FormField>
        <FormField label="Luggage" htmlFor="rq-lug" hint="e.g. 1 large + 1 cabin bag each, golf bags, stroller">
          <input id="rq-lug" className={controlClass} value={value.luggage_notes ?? ""} onChange={(e) => set({ luggage_notes: e.target.value })} />
        </FormField>
      </div>
      <Toggle id="rq-at" checked={value.airport_transfers} onChange={(airport_transfers) => set({ airport_transfers })} label="Airport transfers needed" />
      <Toggle id="rq-ls" checked={value.local_sightseeing_transport} onChange={(local_sightseeing_transport) => set({ local_sightseeing_transport })} label="Transport for local sightseeing" />
    </div>
  );
}

// ------------------------------------------------------------------ 8 Budget
export function StepBudget({ value, set, options }: StepProps) {
  const travellers = value.adults + value.children;
  const per = value.budget_per_person ? Number(value.budget_per_person) : null;
  const total = value.budget_total ? Number(value.budget_total) : null;
  const dec = (s: string) => (s.trim() === "" ? null : s.replace(",", "."));
  return (
    <div className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-3">
        <FormField label="Budget per person" htmlFor="rq-bpp" hint={per && travellers ? `≈ ${formatMoney(per * travellers, value.currency)} for ${travellers}` : undefined}>
          <input id="rq-bpp" inputMode="decimal" className={controlClass} value={value.budget_per_person ?? ""} onChange={(e) => set({ budget_per_person: dec(e.target.value) })} />
        </FormField>
        <FormField label="Total group budget" htmlFor="rq-bt" hint={total && travellers ? `≈ ${formatMoney(total / travellers, value.currency)} per person` : undefined}>
          <input id="rq-bt" inputMode="decimal" className={controlClass} value={value.budget_total ?? ""} onChange={(e) => set({ budget_total: dec(e.target.value) })} />
        </FormField>
        <FormField label="Currency" htmlFor="rq-cur">
          <NativeSelect id="rq-cur" value={value.currency} onChange={(e) => set({ currency: e.target.value })}>
            {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
          </NativeSelect>
        </FormField>
      </div>
      <FormField label="Budget flexibility" htmlFor="rq-flex">
        <Segmented id="rq-flex" label="Budget flexibility" value={value.budget_flexibility ?? ""} onChange={(v) => set({ budget_flexibility: v || null })}
          options={[...choices(options.budget_flexibility), { value: "", label: "Not set" }]} />
      </FormField>
      <FormField label="Preferred travel class" htmlFor="rq-class">
        <Segmented id="rq-class" label="Travel class" value={value.travel_class ?? ""} onChange={(v) => set({ travel_class: v || null })}
          options={[...choices(options.travel_classes), { value: "", label: "Not set" }]} />
      </FormField>
    </div>
  );
}

// ------------------------------------------------------------------ 9 Notes
export function StepNotes({ value, set }: StepProps) {
  return (
    <div className="space-y-5">
      <FormField label="Additional customer requirements" htmlFor="rq-add" hint="Celebrations, accessibility, special requests… (may appear in proposals)">
        <textarea id="rq-add" rows={5} maxLength={5000} className={cn(controlClass, "h-auto py-2")} value={value.additional_requirements ?? ""} onChange={(e) => set({ additional_requirements: e.target.value })} />
      </FormField>
      <FormField label="Internal notes" htmlFor="rq-int-notes" hint="For YANA staff only; never shown to agents or customers.">
        <textarea id="rq-int-notes" rows={4} maxLength={5000} className={cn(controlClass, "h-auto py-2")} value={value.internal_notes ?? ""} onChange={(e) => set({ internal_notes: e.target.value })} />
      </FormField>
    </div>
  );
}
