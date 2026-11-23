"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { UseQueryResult } from "@tanstack/react-query";
import { Inbox } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { EnquiryStatusBadge } from "@/components/common/status-badge";
import { formatDate, tripLength } from "@/lib/format";
import type { Enquiry, Page } from "@/types/crm";

export function travelWindow(e: Pick<Enquiry, "travel_start_date" | "travel_end_date">) {
  if (!e.travel_start_date) return "Dates not set";
  const len = tripLength(e.travel_start_date, e.travel_end_date);
  return `${formatDate(e.travel_start_date)}${len ? ` · ${len.days}D/${len.nights}N` : ""}`;
}

/** Reusable enquiries table (list page, dashboard, agent and customer details). */
export function EnquiriesTable({
  query,
  hideAgent,
  hideCustomer,
  compact,
  emptyText = "No enquiries found.",
  emptyAction,
}: {
  query: UseQueryResult<Page<Enquiry>>;
  hideAgent?: boolean;
  hideCustomer?: boolean;
  /** Narrow containers (dashboard): drop the planner column, show the agent under the customer. */
  compact?: boolean;
  emptyText?: string;
  emptyAction?: React.ReactNode;
}) {
  const router = useRouter();
  if (query.isPending) return <TableSkeleton rows={3} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  if (query.data.items.length === 0) return <EmptyState icon={Inbox} title={emptyText} action={emptyAction} />;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Enquiry</TableHead>
          {!hideCustomer && <TableHead>Customer</TableHead>}
          {!hideAgent && !compact && <TableHead className="hidden md:table-cell">Travel agent</TableHead>}
          <TableHead className="hidden lg:table-cell">Travel</TableHead>
          {!compact && <TableHead className="hidden xl:table-cell">Planner</TableHead>}
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {query.data.items.map((e) => (
          <TableRow key={e.id} className="cursor-pointer" onClick={() => router.push(`/crm/enquiries/${e.id}`)}>
            <TableCell>
              <Link href={`/crm/enquiries/${e.id}`} className="font-mono text-xs font-semibold hover:underline" onClick={(ev) => ev.stopPropagation()}>
                {e.reference}
              </Link>
              <div className="text-xs text-muted-foreground">{formatDate(e.enquiry_date)}</div>
            </TableCell>
            {!hideCustomer && (
              <TableCell>
                <div className="font-medium">{e.customer.name}</div>
                <div className="text-xs text-muted-foreground">
                  {compact ? `${e.travel_agent.company_name} · ` : ""}
                  {e.total_travellers} travellers
                </div>
              </TableCell>
            )}
            {!hideAgent && !compact && <TableCell className="hidden md:table-cell">{e.travel_agent.company_name}</TableCell>}
            <TableCell className="hidden lg:table-cell text-sm">{travelWindow(e)}</TableCell>
            {!compact && (
              <TableCell className="hidden xl:table-cell text-sm">
                {e.assigned_planner?.full_name ?? <span className="text-muted-foreground">Unassigned</span>}
              </TableCell>
            )}
            <TableCell><EnquiryStatusBadge status={e.status} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
