"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDown, ArrowUp, BedDouble, Copy, GripVertical, Pencil, Plus, Trash2, Utensils,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { controlClass, FormField, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { cn } from "@/lib/utils";
import { inventoryApi } from "@/services/inventory";
import { itinerariesApi } from "@/services/itineraries";
import type { Activity, Day, ItineraryDetail, Stay, TimeSlot } from "@/types/itinerary";
import { AddActivityDialog } from "@/features/itinerary-builder/add-activity-dialog";

export const SLOTS: { value: TimeSlot; label: string }[] = [
  { value: "morning", label: "Morning" },
  { value: "afternoon", label: "Afternoon" },
  { value: "full_day", label: "Full day" },
  { value: "evening", label: "Evening" },
];
const FIXED_TYPES = new Set(["arrival", "departure", "check_in", "check_out"]);
const DIET_FLAG: Record<string, [string, string]> = {
  indian_vegetarian: ["vegetarian", "veg"], indian_jain: ["jain", "Jain"], halal: ["halal", "halal"], vegan: ["vegan", "vegan"],
};
const longDate = (iso: string) => new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" }).format(new Date(iso));

export type DragState = { activityId: number; fromDay: number } | null;

type Props = {
  it: ItineraryDetail;
  day: Day;
  stay: Stay | undefined;
  editable: boolean;
  run: (fn: () => Promise<ItineraryDetail>, success?: string) => void;
  drag: DragState;
  setDrag: (d: DragState) => void;
  foodPreferences: string[];
};

function MealRow({ it, day, meal, editable, run, foodPreferences }: Omit<Props, "stay" | "drag" | "setDrag"> & { meal: "breakfast" | "lunch" | "dinner" }) {
  const restaurants = useQuery({
    queryKey: ["inventory", "restaurants", "list", { city_id: day.city_id, active: true, page_size: 100 }],
    queryFn: () => inventoryApi.list("restaurants", { city_id: day.city_id, active: true, page_size: 100 }),
    enabled: editable,
    staleTime: 60_000,
  });
  const current = day.meals.find((m) => m.meal === meal);
  const value = !current ? "none" : current.arrangement === "restaurant" ? `r:${current.restaurant_id}` : current.arrangement;
  const needs = foodPreferences.filter((f) => f in DIET_FLAG).map((f) => DIET_FLAG[f]);
  const label = meal.charAt(0).toUpperCase() + meal.slice(1);

  if (!editable) {
    return (
      <li><span className="text-muted-foreground">{label}:</span>{" "}
        {!current ? "not included" : current.arrangement === "hotel" ? "at the hotel" : current.restaurant_name ?? <span className="text-amber-700">to be arranged</span>}
      </li>
    );
  }
  return (
    <li className="flex items-center gap-2">
      <label htmlFor={`meal-${day.day_number}-${meal}`} className="w-20 shrink-0 text-muted-foreground">{label}</label>
      <NativeSelect
        id={`meal-${day.day_number}-${meal}`}
        className="h-8 text-xs"
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          const body = v.startsWith("r:") ? { arrangement: "restaurant", restaurant_id: Number(v.slice(2)) } : { arrangement: v };
          run(() => itinerariesApi.setMeal(it.id, day.day_number, meal, body));
        }}
      >
        <option value="hotel">At the hotel</option>
        {(restaurants.data?.items ?? []).map((r) => {
          const ok = needs.every(([flag]) => r[flag] === true);
          const tag = needs.length ? (ok ? ` ✓ ${needs.map((n) => n[1]).join("/")} verified` : " ⚠ diet not verified") : "";
          return <option key={r.id} value={`r:${r.id}`}>{r.name}{r.cuisine ? ` (${String(r.cuisine)})` : ""}{tag}</option>;
        })}
        {current?.arrangement === "restaurant" && current.restaurant_id && !restaurants.data?.items.some((r) => r.id === current.restaurant_id) && (
          <option value={`r:${current.restaurant_id}`}>{current.restaurant_name ?? "Current restaurant"}</option>
        )}
        <option value="own">Own arrangement / to be arranged</option>
        <option value="none">Not included</option>
      </NativeSelect>
    </li>
  );
}

function ActivityEditDialog({ it, activity, onClose, run }: { it: ItineraryDetail; activity: Activity; onClose: () => void; run: Props["run"] }) {
  const [v, setV] = useState({ title: activity.title, description: activity.description ?? "", duration: activity.duration_min ? String(activity.duration_min) : "" });
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Edit activity" formId="activity-edit-form">
      <form
        id="activity-edit-form"
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!v.title.trim()) return;
          run(() => itinerariesApi.updateActivity(it.id, activity.id, {
            title: v.title.trim(), description: v.description.trim() || null, duration_min: v.duration ? Number(v.duration) : null,
          }), "Activity updated");
          onClose();
        }}
      >
        <FormField label="Title" htmlFor="act-title" required>
          <input id="act-title" className={controlClass} value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} autoFocus />
        </FormField>
        <FormField label="Description" htmlFor="act-desc" hint="Shown in the itinerary and proposal">
          <textarea id="act-desc" rows={3} className={cn(controlClass, "h-auto py-2")} value={v.description} onChange={(e) => setV({ ...v, description: e.target.value })} />
        </FormField>
        <FormField label="Duration (minutes)" htmlFor="act-dur">
          <input id="act-dur" inputMode="numeric" className={controlClass} value={v.duration} onChange={(e) => setV({ ...v, duration: e.target.value.replace(/\D/g, "") })} />
        </FormField>
      </form>
    </FormDialog>
  );
}

/** Day-by-day planning: the city of the day and where the group sleeps. Hotels and travel legs follow. */
function DayCities({ it, day, isLast, run }: { it: ItineraryDetail; day: Day; isLast: boolean; run: Props["run"] }) {
  const cities = useQuery({ queryKey: ["inventory", "cities", "list", { active: true, page_size: 100 }], queryFn: () => inventoryApi.list("cities", { active: true, page_size: 100 }), staleTime: 60_000 });
  const options = (cities.data?.items ?? []).map((c) => ({ id: c.id, label: `${String(c.name)}${c.country ? ` (${String((c.country as { name: string }).name)})` : ""}` }))
    .sort((a, b) => a.label.localeCompare(b.label));
  return (
    <div className="mt-2 flex flex-wrap gap-3 text-xs">
      <label className="flex items-center gap-1.5">
        <span className="text-muted-foreground">Day in</span>
        <NativeSelect aria-label={`City of day ${day.day_number}`} className="h-8 w-48 text-xs" value={day.city_id}
          onChange={(e) => { const cityId = Number(e.target.value); run(() => itinerariesApi.updateDay(it.id, day.day_number, { city_id: cityId }), "City changed"); }}>
          {options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </NativeSelect>
      </label>
      {!isLast && (
        <label className="flex items-center gap-1.5">
          <span className="text-muted-foreground">Overnight in</span>
          <NativeSelect aria-label={`Overnight city of day ${day.day_number}`} className="h-8 w-48 text-xs" value={day.overnight_city_id ?? ""}
            onChange={(e) => { const cityId = Number(e.target.value); run(() => itinerariesApi.updateDay(it.id, day.day_number, { overnight_city_id: cityId }), "Overnight city changed"); }}>
            {options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </NativeSelect>
        </label>
      )}
    </div>
  );
}

export function DayEditor({ it, day, stay, editable, run, drag, setDrag, foodPreferences }: Props) {
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState(day.title);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Activity | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [dropTarget, setDropTarget] = useState<number | "end" | null>(null);
  const isFirst = day.day_number === 1;
  const isLast = day.day_number === it.total_days;
  const acts = day.activities;

  const move = (a: Activity, index: number) => {
    // index -1 / length: move to previous/next day
    if (index < 0 && day.day_number > 1) {
      const prev = it.days[day.day_number - 2];
      return run(() => itinerariesApi.moveActivity(it.id, a.id, { day_number: prev.day_number, position: prev.activities.length }));
    }
    if (index >= acts.length && !isLast) {
      return run(() => itinerariesApi.moveActivity(it.id, a.id, { day_number: day.day_number + 1, position: 0 }));
    }
    run(() => itinerariesApi.moveActivity(it.id, a.id, { day_number: day.day_number, position: index }));
  };
  const drop = (position: number) => {
    if (!drag) return;
    const sameDayBefore = drag.fromDay === day.day_number && acts.findIndex((x) => x.id === drag.activityId) < position;
    run(() => itinerariesApi.moveActivity(it.id, drag.activityId, { day_number: day.day_number, position: sameDayBefore ? position - 1 : position }));
    setDrag(null);
    setDropTarget(null);
  };

  return (
    <Card id={`day-${day.day_number}`} className="scroll-mt-6">
      <CardHeader className="flex flex-row flex-wrap items-start gap-4 border-b">
        <div className="flex size-14 shrink-0 flex-col items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <span className="text-[10px] font-medium tracking-widest uppercase opacity-70">Day</span>
          <span className="font-heading text-xl leading-none font-semibold">{String(day.day_number).padStart(2, "0")}</span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium tracking-wide text-brand-teal uppercase">{longDate(day.date)} · {day.city}</p>
          {renaming ? (
            <form
              className="mt-1 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (title.trim()) run(() => itinerariesApi.updateDay(it.id, day.day_number, { title: title.trim(), description: day.description }));
                setRenaming(false);
              }}
            >
              <input aria-label="Day title" className={cn(controlClass, "h-9")} value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
              <Button type="submit" size="sm">Save</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => { setTitle(day.title); setRenaming(false); }}>Cancel</Button>
            </form>
          ) : (
            <h3 className="font-heading text-xl font-semibold">{day.title}</h3>
          )}
          {editable && !renaming && <DayCities it={it} day={day} isLast={isLast} run={run} />}
        </div>
        {editable && !renaming && (
          <div className="flex flex-wrap gap-1">
            <Button variant="ghost" size="icon" title="Rename day" aria-label={`Rename day ${day.day_number}`} onClick={() => { setTitle(day.title); setRenaming(true); }}><Pencil /></Button>
            {!isLast && <Button variant="ghost" size="icon" title="Add a day after" aria-label={`Add a day after day ${day.day_number}`} onClick={() => run(() => itinerariesApi.addDayAfter(it.id, day.day_number), `Day added after day ${day.day_number}`)}><Plus /></Button>}
            {!isFirst && !isLast && <Button variant="ghost" size="icon" title="Duplicate day" aria-label={`Duplicate day ${day.day_number}`} onClick={() => run(() => itinerariesApi.duplicateDay(it.id, day.day_number), "Day duplicated")}><Copy /></Button>}
            {!isFirst && !isLast && <Button variant="ghost" size="icon" title="Remove day" aria-label={`Remove day ${day.day_number}`} onClick={() => setConfirmRemove(true)}><Trash2 /></Button>}
          </div>
        )}
      </CardHeader>
      <CardContent className="grid gap-5 pt-5 lg:grid-cols-[minmax(0,1fr)_17rem]">
        <div>
          <ul className="space-y-1.5" aria-label={`Activities on day ${day.day_number}`}>
            {acts.map((a, i) => {
              const fixed = FIXED_TYPES.has(a.activity_type);
              return (
                <li
                  key={a.id}
                  draggable={editable && !fixed}
                  onDragStart={() => setDrag({ activityId: a.id, fromDay: day.day_number })}
                  onDragEnd={() => { setDrag(null); setDropTarget(null); }}
                  onDragOver={(e) => { if (drag && editable) { e.preventDefault(); setDropTarget(i); } }}
                  onDrop={(e) => { e.preventDefault(); drop(i); }}
                  className={cn(
                    "group flex items-center gap-2 rounded-lg border bg-card px-2 py-2",
                    dropTarget === i && "border-t-2 border-t-brand-teal",
                    drag?.activityId === a.id && "opacity-40",
                  )}
                >
                  {editable && !fixed ? <GripVertical className="size-4 shrink-0 cursor-grab text-muted-foreground" aria-hidden /> : <span className="w-4 shrink-0" />}
                  {a.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element -- authenticated API image
                    <img src={a.image_url} alt="" className="size-9 shrink-0 rounded-md object-cover" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className={cn("truncate text-sm", a.activity_type === "sightseeing" && "font-medium")} title={a.title}>{a.title}</p>
                    {a.description && <p className="truncate text-xs text-muted-foreground" title={a.description}>{a.description}</p>}
                  </div>
                  {editable && !fixed ? (
                    <>
                      <NativeSelect aria-label={`Time of day for ${a.title}`} className="h-8 w-28 text-xs" value={a.time_slot}
                        onChange={(e) => {
                          const slot = e.target.value as TimeSlot; // read now: React restores the controlled value before the save runs
                          run(() => itinerariesApi.updateActivity(it.id, a.id, { time_slot: slot }));
                        }}>
                        {SLOTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                      </NativeSelect>
                      <div className="flex">
                        <Button variant="ghost" size="icon" aria-label={`Move ${a.title} up`} title={i === 0 ? "Move to previous day" : "Move up"} disabled={i === 0 && isFirst} onClick={() => move(a, i - 1)}><ArrowUp /></Button>
                        <Button variant="ghost" size="icon" aria-label={`Move ${a.title} down`} title={i === acts.length - 1 ? "Move to next day" : "Move down"} disabled={i === acts.length - 1 && isLast} onClick={() => move(a, i + 1)}><ArrowDown /></Button>
                        <Button variant="ghost" size="icon" aria-label={`Edit ${a.title}`} title="Edit" onClick={() => setEditing(a)}><Pencil /></Button>
                        <Button variant="ghost" size="icon" aria-label={`Remove ${a.title}`} title="Remove" onClick={() => run(() => itinerariesApi.removeActivity(it.id, a.id), `Removed “${a.title}”`)}><Trash2 /></Button>
                      </div>
                    </>
                  ) : (
                    <span className="shrink-0 text-xs text-muted-foreground">{SLOTS.find((s) => s.value === a.time_slot)?.label}</span>
                  )}
                </li>
              );
            })}
          </ul>
          {editable && (
            <div
              onDragOver={(e) => { if (drag) { e.preventDefault(); setDropTarget("end"); } }}
              onDragLeave={() => setDropTarget(null)}
              onDrop={(e) => { e.preventDefault(); drop(acts.length); }}
              className={cn("mt-2 rounded-lg border border-dashed p-1 transition-colors", dropTarget === "end" ? "border-brand-teal bg-accent" : drag ? "border-border" : "border-transparent")}
            >
              <Button variant="ghost" size="sm" className="w-full justify-start text-brand-teal" onClick={() => setAdding(true)}>
                <Plus aria-hidden /> {drag ? "Drop here to move to this day" : "Add sightseeing or free time"}
              </Button>
            </div>
          )}
        </div>

        <aside className="space-y-3 rounded-xl bg-muted/40 p-4 text-sm">
          <div className="flex gap-2">
            <Utensils className="mt-1.5 size-4 shrink-0 text-brand-teal" aria-hidden />
            <ul className="min-w-0 flex-1 space-y-1.5" aria-label="Meals">
              {(["breakfast", "lunch", "dinner"] as const).filter((m) => editable || day.meals.some((x) => x.meal === m)).map((m) => (
                <MealRow key={m} it={it} day={day} meal={m} editable={editable} run={run} foodPreferences={foodPreferences} />
              ))}
            </ul>
          </div>
          {day.overnight_city && (
            <p className="flex gap-2">
              <BedDouble className="mt-0.5 size-4 shrink-0 text-brand-teal" aria-hidden />
              <span>Overnight in {day.overnight_city}{stay?.hotel ? <span className="block text-xs text-muted-foreground">{stay.hotel.name}</span> : <span className="block text-xs text-amber-700">no hotel selected</span>}</span>
            </p>
          )}
        </aside>
      </CardContent>

      {adding && <AddActivityDialog it={it} day={day} onClose={() => setAdding(false)} run={run} />}
      {editing && <ActivityEditDialog it={it} activity={editing} onClose={() => setEditing(null)} run={run} />}
      <ConfirmDialog
        open={confirmRemove}
        onOpenChange={setConfirmRemove}
        title={`Remove day ${day.day_number}?`}
        description="Its activities and meals are removed and the trip becomes one night shorter. Saved versions are not affected."
        confirmLabel="Remove day"
        destructive
        onConfirm={() => { setConfirmRemove(false); run(() => itinerariesApi.removeDay(it.id, day.day_number), `Day ${day.day_number} removed`); }}
      />
    </Card>
  );
}
