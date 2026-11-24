"use client";

import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { PencilRuler } from "lucide-react";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { EnquiryStatusBadge } from "@/components/common/status-badge";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { enquiriesApi } from "@/services/crm";
import { CreateItineraryDialog } from "./create-itinerary";

const PAGE_SIZE = 20;

/** Menu entry "Create Itinerary": choose the enquiry, then plan the itinerary day by day. */
export function CreateItineraryPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [enquiryId, setEnquiryId] = useState<number | null>(null);
  const params = { q, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["enquiries", "list", params], queryFn: () => enquiriesApi.list(params), placeholderData: keepPreviousData });
  return (
    <>
      <PageHeader title="Create Itinerary" description="Choose the enquiry, then plan the itinerary day by day: cities, overnight stays, sightseeing, restaurants and hotels." />
      <Card className="p-4 sm:p-5">
        <div className="mb-4"><SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Reference, customer or agent" label="Search enquiries" /></div>
        {list.isPending ? <TableSkeleton /> : list.isError ? <ErrorState message={list.error.message} onRetry={() => list.refetch()} /> : list.data.items.length === 0 ? (
          <EmptyState icon={PencilRuler} title="No enquiries" description="Create an enquiry first (CRM → Enquiries)." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow><TableHead>Enquiry</TableHead><TableHead className="hidden md:table-cell">Agent</TableHead><TableHead className="hidden md:table-cell">Travel</TableHead><TableHead>Status</TableHead><TableHead className="text-right" /></TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell><div className="font-mono text-xs font-semibold">{e.reference}</div><div className="text-sm">{e.customer.name}</div></TableCell>
                    <TableCell className="hidden text-sm md:table-cell">{e.travel_agent.company_name}</TableCell>
                    <TableCell className="hidden text-sm md:table-cell">{e.travel_start_date ? formatDate(e.travel_start_date) : "—"} · {e.total_travellers} pax</TableCell>
                    <TableCell><EnquiryStatusBadge status={e.status} /></TableCell>
                    <TableCell className="text-right"><Button size="sm" onClick={() => setEnquiryId(e.id)} aria-label={`Create itinerary for ${e.reference}`}><PencilRuler aria-hidden /> Create itinerary</Button></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />
          </>
        )}
      </Card>
      {enquiryId && <CreateItineraryDialog key={enquiryId} enquiryId={enquiryId} onClose={() => setEnquiryId(null)} />}
    </>
  );
}
