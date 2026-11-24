"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BedDouble, Bus, CheckCircle2, TrainFront } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { DemoBadge } from "@/features/inventory/badges";
import { EstimateNote } from "@/features/itineraries/parts";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { inventoryApi } from "@/services/inventory";
import { itinerariesApi } from "@/services/itineraries";
import type { ItineraryDetail, Stay } from "@/types/itinerary";

type Run = (fn: () => Promise<ItineraryDetail>, success?: string) => void;

export function LiveChecks({ it }: { it: ItineraryDetail }) {
  return (
    <Card className={cn(it.warnings.length ? "border-amber-200 bg-amber-50/50" : "border-emerald-200 bg-emerald-50/50")}>
      <CardHeader>
        <CardTitle className={cn("flex items-center gap-2 text-base", it.warnings.length ? "text-amber-900" : "text-emerald-800")}>
          {it.warnings.length ? <AlertTriangle className="size-4" aria-hidden /> : <CheckCircle2 className="size-4" aria-hidden />}
          {it.warnings.length ? `Checks: ${it.warnings.length} to review` : "Checks: all clear"}
        </CardTitle>
        <p className="text-xs text-muted-foreground">Re-checked after every change.</p>
      </CardHeader>
      {it.warnings.length > 0 && (
        <CardContent>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-amber-900" aria-live="polite">{it.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </CardContent>
      )}
    </Card>
  );
}

function ReplaceHotelDialog({ it, stay, onClose, run }: { it: ItineraryDetail; stay: Stay; onClose: () => void; run: Run }) {
  const hotels = useQuery({
    queryKey: ["inventory", "hotels", "list", { city_id: stay.city_id, active: true, page_size: 100 }],
    queryFn: () => inventoryApi.list("hotels", { city_id: stay.city_id, active: true, page_size: 100 }),
  });
  const [picked, setPicked] = useState<number | null>(stay.hotel?.id ?? null);
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Hotel in ${stay.city}`} description={`${stay.nights} night${stay.nights === 1 ? "" : "s"} from day ${stay.check_in_day}. Prices are estimates; availability is not verified.`}
      formId="replace-hotel-form" submitLabel="Use this hotel" wide>
      <form id="replace-hotel-form" onSubmit={(e) => {
        e.preventDefault();
        if (picked && picked !== stay.hotel?.id) run(() => itinerariesApi.replaceHotel(it.id, stay.id, picked), "Hotel replaced");
        onClose();
      }}>
        {hotels.isPending ? <p className="text-sm text-muted-foreground">Loading…</p> : (hotels.data?.items.length ?? 0) === 0 ? (
          <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No active hotels in {stay.city}. An administrator can add one under Destination Inventory → Hotels.</p>
        ) : (
          <ul role="radiogroup" aria-label="Hotels" className="max-h-96 space-y-2 overflow-y-auto pr-1">
            {hotels.data!.items.map((h) => {
              const rooms = (h.room_types as { name: string; base_price: string | null; currency: string }[] | undefined) ?? [];
              const cheapest = rooms.filter((r) => Number(r.base_price) > 0).sort((x, y) => Number(x.base_price) - Number(y.base_price))[0];
              const from = cheapest ? Number(cheapest.base_price) : undefined;
              const on = picked === h.id;
              return (
                <li key={h.id}>
                  <button type="button" role="radio" aria-checked={on} onClick={() => setPicked(h.id)}
                    className={cn("flex w-full items-center gap-3 rounded-lg border p-2.5 text-left transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none", on ? "border-brand-teal bg-accent" : "hover:bg-muted/60")}>
                    {h.primary_image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element -- authenticated API image
                      <img src={h.primary_image_url} alt="" className="size-12 shrink-0 rounded-md object-cover" />
                    ) : <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-muted"><BedDouble className="size-5 text-muted-foreground" aria-hidden /></span>}
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">{h.name} <span className="text-brand-gold">{typeof h.star_rating === "number" ? "★".repeat(h.star_rating) : ""}</span> {h.is_demo && <DemoBadge className="ml-1 align-middle" />}</span>
                      <span className="block text-xs text-muted-foreground">
                        {from ? `from ${formatMoney(from, cheapest.currency)} / room / night (estimate)` : "no price in inventory"}
                        {h.id === stay.hotel?.id ? " · current choice" : ""}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </form>
    </FormDialog>
  );
}

export function HotelsPanel({ it, editable, run }: { it: ItineraryDetail; editable: boolean; run: Run }) {
  const [replacing, setReplacing] = useState<Stay | null>(null);
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Hotels</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {it.stays.map((s) => (
          <div key={s.id} className="flex items-start gap-3 text-sm">
            <div className="min-w-0 flex-1">
              <p className="text-xs text-muted-foreground">{s.city} · {s.nights}N from day {s.check_in_day}</p>
              <p className={cn("font-medium", !s.hotel && "text-amber-700")}>
                {s.hotel ? <Link href={`/inventory/hotels/${s.hotel.id}`} className="hover:underline">{s.hotel.name}</Link> : "No hotel selected"}{" "}
                {s.hotel?.stars ? <span className="text-brand-gold">{"★".repeat(s.hotel.stars)}</span> : null}
              </p>
              {s.estimated_cost && <p className="text-xs text-muted-foreground">{formatMoney(s.estimated_cost, it.currency)} <EstimateNote /></p>}
            </div>
            {editable && <Button size="sm" variant="outline" onClick={() => setReplacing(s)} aria-label={`Replace hotel in ${s.city}`}>Replace</Button>}
          </div>
        ))}
      </CardContent>
      {replacing && <ReplaceHotelDialog it={it} stay={replacing} onClose={() => setReplacing(null)} run={run} />}
    </Card>
  );
}

export function TransportPanel({ it, editable, run }: { it: ItineraryDetail; editable: boolean; run: Run }) {
  const vehicles = useQuery({
    queryKey: ["inventory", "vehicles", "list", { active: true, page_size: 100 }],
    queryFn: () => inventoryApi.list("vehicles", { active: true, page_size: 100 }),
    enabled: editable,
  });
  const currentId = vehicles.data?.items.find((v) => v.name === it.vehicle)?.id;
  const legs = it.transports.filter((t) => t.kind === "intercity");
  // "By road" returns a leg to the trip's own road vehicle type (minibus / coach / car).
  const roadModes = it.transports.map((t) => t.mode).filter((m) => m !== "train");
  const roadMode = roadModes.sort((a, b) => roadModes.filter((x) => x === b).length - roadModes.filter((x) => x === a).length)[0] ?? "coach";
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Transport</CardTitle></CardHeader>
      <CardContent className="space-y-4 text-sm">
        {editable ? (
          <label className="block space-y-1">
            <span className="text-xs text-muted-foreground">Vehicle for the trip</span>
            <NativeSelect value={currentId ? String(currentId) : ""} onChange={(e) => {
              // Read the choice now: React restores the controlled value before the save runs.
              const vehicleId = e.target.value ? Number(e.target.value) : null;
              run(() => itinerariesApi.setVehicle(it.id, vehicleId), "Vehicle changed");
            }}>
              <option value="">No vehicle</option>
              {vehicles.data?.items.map((v) => <option key={v.id} value={v.id}>{v.name} · {String(v.passenger_capacity)} seats</option>)}
            </NativeSelect>
          </label>
        ) : <p>{it.vehicle ?? "No vehicle assigned"}</p>}
        <ul className="space-y-2">
          {legs.map((l) => (
            <li key={l.id} className="flex items-center gap-2">
              {l.mode === "train" ? <TrainFront className="size-4 shrink-0 text-brand-teal" aria-hidden /> : <Bus className="size-4 shrink-0 text-brand-teal" aria-hidden />}
              <span className="min-w-0 flex-1">
                <span className="block">Day {l.day_number}: {l.from_city} → {l.to_city}</span>
                {l.distance_km ? <span className="text-xs text-muted-foreground">≈ {l.distance_km} km <EstimateNote /></span> : null}
              </span>
              {editable && (
                <NativeSelect aria-label={`Mode for ${l.from_city} to ${l.to_city}`} className="h-8 w-28 text-xs" value={l.mode === "train" ? "train" : "road"}
                  onChange={(e) => {
                    const mode = e.target.value === "train" ? "train" : roadMode; // read now, not inside the async save
                    run(() => itinerariesApi.setLegMode(it.id, l.id, mode), mode === "train" ? "Leg set to train" : "Leg set to road");
                  }}>
                  <option value="road">By road</option>
                  <option value="train">By train</option>
                </NativeSelect>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export function CostSummary({ it }: { it: ItineraryDetail }) {
  return (
    <Card>
      <CardContent className="space-y-1 pt-6 text-sm">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Estimated cost</p>
        <p className="font-heading text-2xl font-semibold">{formatMoney(it.cost_per_person, it.currency)} <span className="font-sans text-sm font-normal text-muted-foreground">per person</span></p>
        <p className="text-muted-foreground">{formatMoney(it.total_cost, it.currency)} total · <EstimateNote />{it.unknown_cost_items ? ` · ${it.unknown_cost_items} unpriced` : ""}</p>
      </CardContent>
    </Card>
  );
}
