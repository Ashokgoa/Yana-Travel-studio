"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import { Segmented } from "@/components/common/choice-controls";
import { controlClass, FormField, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { humanize } from "@/features/inventory/resource-config";
import { cn } from "@/lib/utils";
import { inventoryApi } from "@/services/inventory";
import { itinerariesApi } from "@/services/itineraries";
import type { Day, ItineraryDetail, TimeSlot } from "@/types/itinerary";

const SLOT_OPTIONS = [
  { value: "morning", label: "Morning" },
  { value: "afternoon", label: "Afternoon" },
  { value: "full_day", label: "Full day" },
  { value: "evening", label: "Evening" },
];

export function AddActivityDialog({
  it, day, onClose, run,
}: { it: ItineraryDetail; day: Day; onClose: () => void; run: (fn: () => Promise<ItineraryDetail>, success?: string) => void }) {
  const [kind, setKind] = useState<"sightseeing" | "free_time" | "custom">("sightseeing");
  const [slot, setSlot] = useState<TimeSlot>("afternoon");
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState("");
  const [error, setError] = useState<string | null>(null);

  const attractions = useQuery({
    queryKey: ["inventory", "attractions", "list", { city_id: day.city_id, active: true, page_size: 100 }],
    queryFn: () => inventoryApi.list("attractions", { city_id: day.city_id, active: true, page_size: 100 }),
  });
  const usedOn = useMemo(() => {
    const m = new Map<number, number>();
    for (const d of it.days) for (const a of d.activities) if (a.attraction_id && !m.has(a.attraction_id)) m.set(a.attraction_id, d.day_number);
    return m;
  }, [it.days]);
  const list = (attractions.data?.items ?? []).filter((a) => !q || a.name.toLowerCase().includes(q.toLowerCase()));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (kind === "sightseeing") {
      if (!picked) return setError("Choose a sightseeing item.");
      run(() => itinerariesApi.addActivity(it.id, day.day_number, { time_slot: slot, attraction_id: picked }), "Sightseeing added");
    } else {
      const t = title.trim() || (kind === "free_time" ? "Free time" : "");
      if (!t) return setError("Enter a title.");
      run(() => itinerariesApi.addActivity(it.id, day.day_number, {
        time_slot: slot, activity_type: kind, title: t, description: description.trim() || undefined,
        duration_min: duration ? Number(duration) : undefined,
      }), kind === "free_time" ? "Free time added" : "Activity added");
    }
    onClose();
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Add to day ${day.day_number} · ${day.city}`} formId="add-activity-form" submitLabel="Add" wide>
      <form id="add-activity-form" className="space-y-5" onSubmit={submit}>
        <div className="flex flex-wrap items-center gap-3">
          <Segmented label="What to add" value={kind} onChange={(v) => { setKind(v as typeof kind); setError(null); }}
            options={[{ value: "sightseeing", label: "Sightseeing" }, { value: "free_time", label: "Free time" }, { value: "custom", label: "Custom" }]} />
          <NativeSelect aria-label="Time of day" className="w-36" value={slot} onChange={(e) => setSlot(e.target.value as TimeSlot)}>
            {SLOT_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </NativeSelect>
        </div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

        {kind === "sightseeing" ? (
          <div className="space-y-3">
            <input aria-label="Search sightseeing" placeholder={`Search sightseeing in ${day.city}`} className={controlClass} value={q} onChange={(e) => setQ(e.target.value)} />
            {attractions.isPending ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : list.length === 0 ? (
              <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                No active sightseeing in {day.city} in the inventory{q ? " matching your search" : ""}. An administrator can add it under Destination Inventory → Sightseeing.
              </p>
            ) : (
              <ul role="radiogroup" aria-label="Sightseeing" className="max-h-80 space-y-2 overflow-y-auto pr-1">
                {list.map((a) => {
                  const on = picked === a.id;
                  const used = usedOn.get(a.id);
                  return (
                    <li key={a.id}>
                      <button
                        type="button"
                        role="radio"
                        aria-checked={on}
                        onClick={() => setPicked(a.id)}
                        className={cn("flex w-full items-center gap-3 rounded-lg border p-2 text-left transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                          on ? "border-brand-teal bg-accent" : "hover:bg-muted/60")}
                      >
                        {a.primary_image_url ? (
                          // eslint-disable-next-line @next/next/no-img-element -- authenticated API image
                          <img src={a.primary_image_url} alt="" className="size-11 shrink-0 rounded-md object-cover" />
                        ) : (
                          <span className="flex size-11 shrink-0 items-center justify-center rounded-md bg-muted"><Camera className="size-4 text-muted-foreground" aria-hidden /></span>
                        )}
                        <span className="min-w-0 flex-1">
                          <span className="block font-medium">{a.name}</span>
                          <span className="block text-xs text-muted-foreground">
                            {humanize(String(a.category))}
                            {a.recommended_duration_min ? ` · about ${Math.round(Number(a.recommended_duration_min) / 6) / 10} h` : ""}
                            {a.child_friendly === false ? " · not for children" : ""}
                          </span>
                        </span>
                        {used && <span className="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">already on day {used}</span>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Title" htmlFor="aa-title" required={kind === "custom"} className="sm:col-span-2" hint={kind === "free_time" ? "Optional, e.g. ‘Shopping at leisure’" : undefined}>
              <input id="aa-title" className={controlClass} placeholder={kind === "free_time" ? "Free time" : "e.g. Welcome dinner with live music"} value={title} onChange={(e) => setTitle(e.target.value)} />
            </FormField>
            <FormField label="Description" htmlFor="aa-desc" className="sm:col-span-2">
              <textarea id="aa-desc" rows={2} className={cn(controlClass, "h-auto py-2")} value={description} onChange={(e) => setDescription(e.target.value)} />
            </FormField>
            <FormField label="Duration (minutes)" htmlFor="aa-dur">
              <input id="aa-dur" inputMode="numeric" className={controlClass} value={duration} onChange={(e) => setDuration(e.target.value.replace(/\D/g, ""))} />
            </FormField>
          </div>
        )}
      </form>
    </FormDialog>
  );
}
