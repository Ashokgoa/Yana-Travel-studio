"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BedDouble, Bus, Calculator, Camera, FileText, History, Info, LogIn, LogOut, PencilLine, Plane, Sun, TrainFront, Utensils } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, TableSkeleton } from "@/components/common/states";
import { EstimateNote, RouteMap, StrategyBadge } from "@/features/itineraries/parts";
import { DemoBadge } from "@/features/inventory/badges";
import { formatDate, formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { itinerariesApi } from "@/services/itineraries";
import type { Activity, Day, ItineraryDetail, Stay, Transport } from "@/types/itinerary";

const SLOT_ORDER = ["morning", "afternoon", "full_day", "evening"] as const;
const SLOT_LABEL: Record<string, string> = { morning: "Morning", afternoon: "Afternoon", full_day: "Full day", evening: "Evening" };
const ICON: Record<string, typeof Sun> = {
  arrival: Plane, departure: Plane, transfer: Bus, check_in: LogIn, check_out: LogOut, sightseeing: Camera, free_time: Sun,
};
const longDate = (iso: string) => new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" }).format(new Date(iso));
const hm = (m: number | null) => (m ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min` : null);

function ActivityRow({ a }: { a: Activity }) {
  const Icon = ICON[a.activity_type] ?? Info;
  return (
    <li className="flex gap-3">
      {a.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element -- authenticated API image
        <img src={a.image_url} alt="" className="size-12 shrink-0 rounded-lg object-cover" loading="lazy" />
      ) : (
        <span className={cn("flex size-12 shrink-0 items-center justify-center rounded-lg", a.activity_type === "sightseeing" ? "bg-accent text-accent-foreground" : "bg-muted text-muted-foreground")}>
          <Icon className="size-4" aria-hidden />
        </span>
      )}
      <div className="min-w-0 pt-0.5">
        <p className={cn("text-sm", a.activity_type === "sightseeing" && "font-medium")}>{a.title}</p>
        {(a.description || (a.activity_type === "sightseeing" && a.duration_min)) && (
          <p className="text-xs text-muted-foreground">
            {a.activity_type === "sightseeing" && a.duration_min ? `about ${hm(a.duration_min)}` : null}
            {a.activity_type === "sightseeing" && a.duration_min && a.description ? " · " : null}
            {a.description}
          </p>
        )}
      </div>
    </li>
  );
}

function DayCard({ day, stay, legs }: { day: Day; stay: Stay | undefined; legs: Transport[] }) {
  const slots = SLOT_ORDER.map((s) => [s, day.activities.filter((a) => a.time_slot === s)] as const).filter(([, list]) => list.length);
  return (
    <Card id={`day-${day.day_number}`} className="scroll-mt-6">
      <CardHeader className="flex flex-row items-start gap-4 border-b">
        <div className="flex size-14 shrink-0 flex-col items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <span className="text-[10px] font-medium tracking-widest uppercase opacity-70">Day</span>
          <span className="font-heading text-xl leading-none font-semibold">{String(day.day_number).padStart(2, "0")}</span>
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium tracking-wide text-brand-teal uppercase">{longDate(day.date)} · {day.city}</p>
          <CardTitle className="text-xl">{day.title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="grid gap-5 pt-5 md:grid-cols-[minmax(0,1fr)_15rem]">
        <div className="space-y-4">
          {slots.map(([slot, list]) => (
            <div key={slot}>
              <p className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">{SLOT_LABEL[slot]}</p>
              <ul className="space-y-2.5">{list.map((a) => <ActivityRow key={a.id} a={a} />)}</ul>
            </div>
          ))}
        </div>
        <aside className="space-y-3 rounded-xl bg-muted/40 p-4 text-sm">
          {legs.map((l) => (
            <p key={l.id} className="flex gap-2">
              {l.mode === "train" ? <TrainFront className="mt-0.5 size-4 shrink-0 text-brand-teal" aria-hidden /> : <Bus className="mt-0.5 size-4 shrink-0 text-brand-teal" aria-hidden />}
              <span>
                {l.kind === "airport_transfer" ? "Airport transfer" : `${l.from_city} → ${l.to_city}`}
                {l.mode === "train" ? " by train" : l.vehicle ? ` · ${l.vehicle}` : ""}
                {l.distance_km ? <span className="block text-xs text-muted-foreground">≈ {l.distance_km} km, {hm(l.duration_min)} <EstimateNote /></span> : null}
                {l.note && <span className="block text-xs text-muted-foreground">{l.note}</span>}
              </span>
            </p>
          ))}
          {day.meals.length > 0 && (
            <div className="flex gap-2">
              <Utensils className="mt-0.5 size-4 shrink-0 text-brand-teal" aria-hidden />
              <ul className="space-y-1">
                {day.meals.map((m) => (
                  <li key={m.id}>
                    <span className="capitalize">{m.meal}</span>:{" "}
                    {m.arrangement === "hotel" ? "at the hotel" : m.restaurant_name ? (
                      <span>{m.restaurant_name}{m.cuisine && <span className="text-xs text-muted-foreground"> ({m.cuisine})</span>}</span>
                    ) : <span className="text-amber-700" title={m.note ?? undefined}>to be arranged</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {day.overnight_city && (
            <p className="flex gap-2">
              <BedDouble className="mt-0.5 size-4 shrink-0 text-brand-teal" aria-hidden />
              <span>Overnight in {day.overnight_city}{stay?.hotel ? <span className="block text-xs text-muted-foreground">{stay.hotel.name}</span> : <span className="block text-xs text-amber-700">hotel to be arranged</span>}</span>
            </p>
          )}
        </aside>
      </CardContent>
    </Card>
  );
}

function StaysCard({ it }: { it: ItineraryDetail }) {
  return (
    <Card>
      <CardHeader><CardTitle>Hotels</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {it.stays.map((s) => (
          <div key={s.id} className="flex gap-3">
            {s.hotel?.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element -- authenticated API image
              <img src={s.hotel.image_url} alt="" className="size-14 shrink-0 rounded-lg object-cover" />
            ) : (
              <span className="flex size-14 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground"><BedDouble className="size-5" aria-hidden /></span>
            )}
            <div className="min-w-0 text-sm">
              <p className="text-xs text-muted-foreground">{s.city} · {s.nights} night{s.nights === 1 ? "" : "s"} from day {s.check_in_day}</p>
              {s.hotel ? (
                <p className="font-medium">
                  <Link href={`/inventory/hotels/${s.hotel.id}`} className="hover:underline">{s.hotel.name}</Link>{" "}
                  <span className="text-brand-gold">{s.hotel.stars ? "★".repeat(s.hotel.stars) : ""}</span>
                  {s.hotel.is_demo && <DemoBadge className="ml-1.5 align-middle" />}
                </p>
              ) : <p className="font-medium text-amber-700">No hotel in inventory</p>}
              <p className="text-xs text-muted-foreground">{s.rooms.map((r) => `${r.count}× ${r.label}`).join(", ")}</p>
              {s.estimated_cost && <p className="text-xs">{formatMoney(s.estimated_cost, it.currency)} <EstimateNote /> · availability not verified</p>}
              {s.alternatives.length > 0 && <p className="text-xs text-muted-foreground">Alternatives: {s.alternatives.map((h) => h.name).join(", ")}</p>}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function CostsCard({ it }: { it: ItineraryDetail }) {
  const groups = ["hotel", "transport", "sightseeing", "meals"];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost estimate</CardTitle>
        <p className="text-xs text-muted-foreground">Indicative only, from inventory prices. Not a quotation; final pricing comes in the Pricing step.</p>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {groups.map((g) => {
          const lines = it.costs.filter((c) => c.category === g);
          if (!lines.length) return null;
          return (
            <div key={g}>
              <p className="mb-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">{g}</p>
              <ul className="space-y-1">
                {lines.map((c, i) => (
                  <li key={i} className="flex justify-between gap-3">
                    <span className="min-w-0 truncate" title={c.description}>{c.description}</span>
                    <span className={cn("shrink-0 tabular-nums", !c.amount && "text-amber-700")}>{c.amount ? formatMoney(c.amount, c.currency) : "no price"}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
        <div className="flex justify-between border-t pt-3 font-semibold">
          <span>Total <EstimateNote /></span><span className="tabular-nums">{formatMoney(it.total_cost, it.currency)}</span>
        </div>
        <div className="flex justify-between text-muted-foreground"><span>Per person</span><span className="tabular-nums">{formatMoney(it.cost_per_person, it.currency)}</span></div>
      </CardContent>
    </Card>
  );
}

export function ItineraryDetailView({ id, version }: { id: number; version?: number }) {
  const q = useQuery({
    queryKey: version ? ["itineraries", "detail", id, "v", version] : ["itineraries", "detail", id],
    queryFn: () => itinerariesApi.get(id, version),
  });
  if (q.isPending) return <TableSkeleton rows={8} />;
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  const it = q.data;
  const countries = [...new Set(it.route.map((r) => r.country))];
  const stayForNight = (dayNumber: number) => it.stays.find((s) => dayNumber >= s.check_in_day && dayNumber < s.check_in_day + s.nights);

  return (
    <>
      <PageHeader
        back={it.enquiry_id ? { href: `/crm/enquiries/${it.enquiry_id}`, label: it.enquiry_reference ?? "Enquiry" } : { href: "/itineraries", label: "Saved itineraries" }}
        title={<span className="flex flex-wrap items-center gap-3">{it.title.split(":")[0]} <StrategyBadge strategy={it.strategy} /></span>}
        description={`${it.customer_name ?? ""} · ${formatDate(it.start_date)} · ${it.total_days} days / ${it.total_nights} nights · Version ${it.version_number} (${it.version_label})`}
        actions={
          <>
            <Link href={`/itineraries/${it.id}/pricing${version ? `?version=${version}` : ""}`} className={buttonVariants({ variant: "outline" })}>
              <Calculator aria-hidden /> Pricing
            </Link>
            <Link href={`/itineraries/${it.id}/proposal${version ? `?version=${version}` : ""}`} className={buttonVariants({ variant: "outline" })}>
              <FileText aria-hidden /> PDF proposal
            </Link>
            <Link href={`/itineraries/${it.id}/edit`} className={buttonVariants()}>
              <PencilLine aria-hidden /> {it.is_locked && it.version_number === it.latest_version_number ? "Edit itinerary" : "Open builder"}
            </Link>
          </>
        }
      />
      {it.version_number !== it.latest_version_number && (
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border bg-muted/50 px-4 py-3 text-sm">
          <History className="size-4 text-muted-foreground" aria-hidden />
          <span className="flex-1">You are viewing an earlier version (v{it.version_number}: {it.version_label}). The latest is v{it.latest_version_number}.</span>
          <Link href={`/itineraries/${it.id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>View latest</Link>
        </div>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card>
          <CardContent className="space-y-4 pt-6">
            <RouteMap route={it.route} />
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[["Days / nights", `${it.total_days} / ${it.total_nights}`], ["Countries", String(countries.length)], ["Cities", String(it.route.length)], ["Road distance", `≈ ${it.total_distance_km.toLocaleString()} km`]].map(([k, v]) => (
                <div key={k} className="rounded-lg bg-muted/50 p-3"><dt className="text-[11px] text-muted-foreground">{k}</dt><dd className="font-heading text-lg font-semibold">{v}</dd></div>
              ))}
            </dl>
            <p className="text-sm"><span className="text-muted-foreground">Transport:</span> {it.vehicle ?? "not assigned"}</p>
            <p className="text-sm"><span className="text-muted-foreground">Estimated:</span> <strong>{formatMoney(it.cost_per_person, it.currency)}</strong> per person · {formatMoney(it.total_cost, it.currency)} total <EstimateNote /></p>
          </CardContent>
        </Card>
        <div className="space-y-6">
          {it.warnings.length > 0 && (
            <Card className="border-amber-200 bg-amber-50/60">
              <CardHeader><CardTitle className="flex items-center gap-2 text-amber-900"><AlertTriangle className="size-4" aria-hidden /> Points to check ({it.warnings.length})</CardTitle></CardHeader>
              <CardContent><ul className="list-disc space-y-1.5 pl-5 text-sm text-amber-900">{it.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></CardContent>
            </Card>
          )}
          <Card>
            <CardHeader><CardTitle>Why this plan</CardTitle></CardHeader>
            <CardContent><ul className="list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">{it.explanations.map((e, i) => <li key={i}>{e}</li>)}</ul></CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <section aria-label="Day by day" className="space-y-4">
          <nav aria-label="Jump to day" className="flex flex-wrap gap-1.5">
            {it.days.map((d) => <a key={d.id} href={`#day-${d.day_number}`} className="rounded-md bg-muted px-2 py-1 text-xs hover:bg-accent">Day {d.day_number}</a>)}
          </nav>
          {it.days.map((d) => (
            <DayCard key={d.id} day={d} stay={stayForNight(d.day_number)} legs={it.transports.filter((t) => t.day_number === d.day_number)} />
          ))}
        </section>
        <div className="space-y-6 xl:sticky xl:top-6 xl:self-start">
          <StaysCard it={it} />
          <CostsCard it={it} />
        </div>
      </div>
    </>
  );
}
