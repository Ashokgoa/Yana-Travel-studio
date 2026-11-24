"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Route } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { NativeSelect } from "@/components/common/form-controls";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { EstimateNote, StrategyBadge } from "@/features/itineraries/parts";
import { formatDate, formatDateTime, formatMoney } from "@/lib/format";
import { itinerariesApi } from "@/services/itineraries";

const PAGE_SIZE = 20;

export function SavedItineraries() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [strategy, setStrategy] = useState("");
  const [page, setPage] = useState(1);
  const params = { q, strategy, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["itineraries", "list", params], queryFn: () => itinerariesApi.list(params), placeholderData: keepPreviousData });

  return (
    <>
      <PageHeader title="Saved Itineraries" description="Every generated itinerary, newest first. To create one, open an enquiry and generate alternatives." />
      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Enquiry reference or title" label="Search itineraries" />
          <NativeSelect aria-label="Strategy" value={strategy} onChange={(e) => { setStrategy(e.target.value); setPage(1); }} className="sm:w-44">
            <option value="">All strategies</option>
            <option value="classic">Classic</option>
            <option value="scenic">Scenic</option>
            <option value="premium">Premium</option>
          </NativeSelect>
        </div>
        {list.isPending ? <TableSkeleton /> : list.isError ? <ErrorState message={list.error.message} onRetry={() => list.refetch()} /> : list.data.items.length === 0 ? (
          <EmptyState icon={Route} title={q || strategy ? "No itineraries match" : "No itineraries yet"} description="Open an enquiry with completed requirements and click “Generate 3 alternatives”." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Itinerary</TableHead>
                  <TableHead className="hidden md:table-cell">Enquiry</TableHead>
                  <TableHead className="hidden lg:table-cell">Route</TableHead>
                  <TableHead>Per person</TableHead>
                  <TableHead className="hidden xl:table-cell">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((it) => (
                  <TableRow key={it.id} className="cursor-pointer" onClick={() => router.push(`/itineraries/${it.id}`)}>
                    <TableCell>
                      <div className="flex items-center gap-2"><StrategyBadge strategy={it.strategy} /><Link href={`/itineraries/${it.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>{it.total_days} days from {formatDate(it.start_date)}</Link></div>
                      <div className="text-xs text-muted-foreground">v{it.version_number} · {it.version_label} · generation #{it.batch}</div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <div className="font-mono text-xs font-semibold">{it.enquiry_reference}</div>
                      <div className="text-xs text-muted-foreground">{it.customer_name}</div>
                    </TableCell>
                    <TableCell className="hidden max-w-md truncate text-sm lg:table-cell">{it.route.map((r) => r.city).join(" → ")}</TableCell>
                    <TableCell className="whitespace-nowrap">{formatMoney(it.cost_per_person, it.currency)} <EstimateNote /></TableCell>
                    <TableCell className="hidden text-sm xl:table-cell">{formatDateTime(it.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
