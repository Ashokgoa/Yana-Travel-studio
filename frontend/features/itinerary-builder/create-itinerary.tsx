"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PencilRuler } from "lucide-react";
import { toast } from "sonner";
import { FormField, NativeSelect, controlClass } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/services/api";
import { requirementsApi } from "@/services/crm";
import { inventoryApi } from "@/services/inventory";
import { itinerariesApi } from "@/services/itineraries";

function daysBetween(a: string | null, b: string | null): number | null {
  if (!a || !b) return null;
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 86_400_000) + 1;
}

/** Start an itinerary by hand: name, start date, number of days and the first city; then plan each day in the builder. */
export function CreateItineraryButton({ enquiryId, primary = true }: { enquiryId: number; primary?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant={primary ? "default" : "outline"} onClick={() => setOpen(true)}><PencilRuler aria-hidden /> Create itinerary</Button>
      {open && <CreateItineraryDialog enquiryId={enquiryId} onClose={() => setOpen(false)} />}
    </>
  );
}

export function CreateItineraryDialog({ enquiryId, onClose }: { enquiryId: number; onClose: () => void }) {
  const router = useRouter();
  const qc = useQueryClient();
  const req = useQuery({ queryKey: ["requirements", enquiryId], queryFn: () => requirementsApi.get(enquiryId) });
  const cities = useQuery({ queryKey: ["inventory", "cities", "list", { active: true, page_size: 100 }], queryFn: () => inventoryApi.list("cities", { active: true, page_size: 100 }) });
  const vehicles = useQuery({ queryKey: ["inventory", "vehicles", "list", { active: true, page_size: 100 }], queryFn: () => inventoryApi.list("vehicles", { active: true, page_size: 100 }) });
  const [form, setForm] = useState<{ title: string; start: string; days: string; city: string; vehicle: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Defaults from the customer requirements, once loaded.
  if (form === null && req.data && cities.data) {
    const firstDest = req.data.destinations.find((d) => d.preference !== "avoid");
    const cityId = firstDest?.city?.id ?? cities.data.items.find((c) => (c.country as { id: number } | undefined)?.id === firstDest?.country.id)?.id;
    setForm({
      title: "", start: req.data.arrival_date ?? "", days: String(daysBetween(req.data.arrival_date, req.data.departure_date) ?? 7),
      city: cityId ? String(cityId) : "", vehicle: "",
    });
  }
  const create = useMutation({
    mutationFn: () => itinerariesApi.createBlank(enquiryId, {
      title: form!.title.trim() || null, start_date: form!.start || null, days: Number(form!.days), city_id: Number(form!.city),
      vehicle_id: form!.vehicle ? Number(form!.vehicle) : null,
    }),
    onSuccess: (it) => {
      toast.success("Itinerary created: now plan each day");
      void qc.invalidateQueries({ queryKey: ["itineraries"] });
      router.push(`/itineraries/${it.id}/edit`);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not create the itinerary"),
  });
  const cityOptions = (cities.data?.items ?? [])
    .map((c) => ({ id: c.id, label: `${String(c.name)}${c.country ? ` (${String((c.country as { name: string }).name)})` : ""}` }))
    .sort((a, b) => a.label.localeCompare(b.label));

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Create itinerary" formId="create-it-form" submitLabel="Create and plan days" pending={create.isPending}
      description="Start with the number of days and the first city. In the builder you then choose, for each day, the city, overnight stay, sightseeing, meals and hotels.">
      {!form ? <p className="text-sm text-muted-foreground">Loading…</p> : (
        <form id="create-it-form" className="space-y-4" onSubmit={(e) => {
          e.preventDefault();
          const n = Number(form.days);
          if (!form.city) { setError("Choose the first city."); return; }
          if (!Number.isInteger(n) || n < 2 || n > 60) { setError("Number of days: 2 to 60."); return; }
          create.mutate();
        }}>
          <FormField label="Name" htmlFor="ci-title" hint="Optional, e.g. European Grand Tour. You can change it later.">
            <input id="ci-title" className={controlClass} maxLength={200} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Start date" htmlFor="ci-start" hint="Arrival day">
              <input id="ci-start" type="date" className={controlClass} value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} />
            </FormField>
            <FormField label="Number of days" htmlFor="ci-days" required>
              <input id="ci-days" type="number" min={2} max={60} className={controlClass} value={form.days} onChange={(e) => setForm({ ...form, days: e.target.value })} />
            </FormField>
          </div>
          <FormField label="First city" htmlFor="ci-city" required error={error ?? undefined} hint="Arrival city; every night starts here until you change the days.">
            <NativeSelect id="ci-city" value={form.city} onChange={(e) => { setForm({ ...form, city: e.target.value }); setError(null); }}>
              <option value="">Choose a city</option>
              {cityOptions.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </NativeSelect>
          </FormField>
          <FormField label="Vehicle" htmlFor="ci-vehicle" hint="Optional; can be chosen later in the builder.">
            <NativeSelect id="ci-vehicle" value={form.vehicle} onChange={(e) => setForm({ ...form, vehicle: e.target.value })}>
              <option value="">No vehicle yet</option>
              {vehicles.data?.items.map((v) => <option key={v.id} value={v.id}>{String(v.name)} · {String(v.passenger_capacity)} seats</option>)}
            </NativeSelect>
          </FormField>
        </form>
      )}
    </FormDialog>
  );
}
