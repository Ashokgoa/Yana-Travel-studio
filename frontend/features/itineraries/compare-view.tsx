"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { avgStars, EstimateNote, RouteMap, StrategyBadge } from "@/features/itineraries/parts";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { enquiriesApi } from "@/services/crm";
import { itinerariesApi } from "@/services/itineraries";
import type { ItinerarySummary } from "@/types/itinerary";
import { Columns3 } from "lucide-react";

type Row = { label: string; render: (i: ItinerarySummary) => React.ReactNode; best?: (items: ItinerarySummary[]) => number | null };

const minBy = (items: ItinerarySummary[], f: (i: ItinerarySummary) => number) =>
  items.length ? items.reduce((best, i) => (f(i) < f(best) ? i : best)).id : null;

const ROWS: Row[] = [
  { label: "Route", render: (i) => <span className="text-sm">{i.route.map((s) => `${s.city} ${s.nights}N`).join(" → ")}</span> },
  { label: "Countries", render: (i) => [...new Set(i.route.map((r) => r.country))].join(", ") },
  { label: "Stops", render: (i) => String(i.route.length) },
  { label: "Hotels (avg ★)", render: (i) => avgStars(i) },
  { label: "Hotels", render: (i) => <ul className="space-y-0.5 text-sm">{i.hotels.map((h, k) => <li key={k}>{h ? `${h.name}${h.stars ? ` ${"★".repeat(h.stars)}` : ""}` : <span className="text-amber-700">No hotel in inventory</span>}</li>)}</ul> },
  { label: "Road distance", render: (i) => <>≈ {i.total_distance_km.toLocaleString()} km <EstimateNote /></>, best: (items) => minBy(items, (i) => i.total_distance_km) },
  { label: "Estimated per person", render: (i) => <span className="font-semibold">{formatMoney(i.cost_per_person, i.currency)}</span>, best: (items) => minBy(items, (i) => Number(i.cost_per_person ?? Infinity)) },
  { label: "Estimated total", render: (i) => <>{formatMoney(i.total_cost, i.currency)} {i.unknown_cost_items > 0 && <span className="text-xs text-muted-foreground">({i.unknown_cost_items} unpriced)</span>}</> },
  { label: "Points to check", render: (i) => (i.warnings_count ? <span className="text-amber-700">{i.warnings_count}</span> : "None"), best: (items) => minBy(items, (i) => i.warnings_count) },
];

export function CompareView({ enquiryId }: { enquiryId: number }) {
  const enquiry = useQuery({ queryKey: ["enquiries", "detail", enquiryId], queryFn: () => enquiriesApi.get(enquiryId) });
  const list = useQuery({ queryKey: ["itineraries", "enquiry", enquiryId], queryFn: () => itinerariesApi.forEnquiry(enquiryId) });

  if (list.isError) return <ErrorState message={list.error.message} onRetry={() => list.refetch()} />;
  if (!list.data || !enquiry.data) return <TableSkeleton rows={8} />;
  const batch = list.data.length ? Math.max(...list.data.map((i) => i.batch)) : 0;
  const items = list.data.filter((i) => i.batch === batch);

  return (
    <>
      <PageHeader
        back={{ href: `/crm/enquiries/${enquiryId}`, label: enquiry.data.reference }}
        title="Compare proposals"
        description={`${enquiry.data.customer.name} · ${items[0]?.total_days ?? ""} days · all costs are estimates`}
      />
      {items.length === 0 ? (
        <EmptyState icon={Columns3} title="No itineraries yet" description="Generate alternatives from the enquiry page first." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr className="border-b">
                <th className="w-44 p-4" />
                {items.map((i) => (
                  <th key={i.id} className="p-4 align-top font-normal">
                    <StrategyBadge strategy={i.strategy} />
                    <p className="mt-2 text-xs text-muted-foreground">{i.strategy_summary}</p>
                    <RouteMap route={i.route} className="mt-3" />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                const best = row.best?.(items);
                return (
                  <tr key={row.label} className="border-b last:border-0">
                    <th scope="row" className="p-4 align-top text-xs font-medium tracking-wide text-muted-foreground uppercase">{row.label}</th>
                    {items.map((i) => (
                      <td key={i.id} className={cn("p-4 align-top text-sm", best === i.id && items.length > 1 && "bg-emerald-50/70")}>
                        {row.render(i)}
                        {best === i.id && items.length > 1 && <span className="ml-2 text-[11px] font-medium text-emerald-700">lowest</span>}
                      </td>
                    ))}
                  </tr>
                );
              })}
              <tr>
                <td className="p-4" />
                {items.map((i) => (
                  <td key={i.id} className="p-4">
                    <Link href={`/itineraries/${i.id}`} className={buttonVariants({ className: "w-full" })}>View day by day</Link>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
