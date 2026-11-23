"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { UseQueryResult } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { ActiveBadge } from "@/components/common/status-badge";
import type { Customer, Page } from "@/types/crm";

export function travellerSummary(adults: number, children: number) {
  const parts = [`${adults} adult${adults === 1 ? "" : "s"}`];
  if (children) parts.push(`${children} child${children === 1 ? "" : "ren"}`);
  return parts.join(", ");
}

/** Reusable customers table (list page, agent detail). */
export function CustomersTable({
  query,
  hideAgent,
  emptyText = "No customers found.",
  emptyAction,
}: {
  query: UseQueryResult<Page<Customer>>;
  hideAgent?: boolean;
  emptyText?: string;
  emptyAction?: React.ReactNode;
}) {
  const router = useRouter();
  if (query.isPending) return <TableSkeleton rows={3} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  if (query.data.items.length === 0) return <EmptyState icon={Users} title={emptyText} action={emptyAction} />;

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Customer</TableHead>
          {!hideAgent && <TableHead className="hidden md:table-cell">Travel agent</TableHead>}
          <TableHead className="hidden sm:table-cell">Travellers</TableHead>
          <TableHead className="hidden lg:table-cell text-right">Enquiries</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {query.data.items.map((c) => (
          <TableRow key={c.id} className="cursor-pointer" onClick={() => router.push(`/crm/customers/${c.id}`)}>
            <TableCell>
              <Link href={`/crm/customers/${c.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                {c.name}
              </Link>
              <div className="text-xs text-muted-foreground">{c.email ?? c.phone ?? ""}</div>
            </TableCell>
            {!hideAgent && <TableCell className="hidden md:table-cell">{c.travel_agent?.company_name ?? <span className="text-muted-foreground">Direct</span>}</TableCell>}
            <TableCell className="hidden sm:table-cell">{travellerSummary(c.adults, c.children)}</TableCell>
            <TableCell className="hidden lg:table-cell text-right tabular-nums">{c.enquiry_count}</TableCell>
            <TableCell><ActiveBadge status={c.is_active} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
