"use client";

import { useState } from "react";
import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { FileText, Palette } from "lucide-react";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/features/auth/auth-provider";
import { StrategyBadge } from "@/features/itineraries/parts";
import { formatDate } from "@/lib/format";
import { itinerariesApi } from "@/services/itineraries";

const PAGE_SIZE = 20;

/** Entry point of the PDF Designer: pick an itinerary; administrators also manage branding. */
export function PdfDesignerHome() {
  const { hasRole } = useAuth();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const params = { q, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["itineraries", "list", params], queryFn: () => itinerariesApi.list(params), placeholderData: keepPreviousData });

  return (
    <>
      <PageHeader
        title="PDF Designer"
        description="Choose an itinerary to design and create its customer PDF: Classic, Premium or Explorer template, agent or YANA branding, sections, photos, price and texts."
        actions={hasRole("admin") ? <Link href="/admin/branding" className={buttonVariants({ variant: "outline" })}><Palette aria-hidden /> Branding and defaults</Link> : undefined}
      />
      <Card className="p-4 sm:p-5">
        <div className="mb-4"><SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Enquiry reference or title" label="Search itineraries" /></div>
        {list.isPending ? <TableSkeleton /> : list.isError ? <ErrorState message={list.error.message} onRetry={() => list.refetch()} /> : list.data.items.length === 0 ? (
          <EmptyState icon={FileText} title={q ? "No itineraries match" : "No itineraries yet"} description="Generate itineraries from an enquiry first." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Itinerary</TableHead>
                  <TableHead className="hidden md:table-cell">Enquiry</TableHead>
                  <TableHead className="hidden lg:table-cell">Route</TableHead>
                  <TableHead className="text-right">PDF</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((it) => (
                  <TableRow key={it.id}>
                    <TableCell>
                      <div className="flex items-center gap-2"><StrategyBadge strategy={it.strategy} /><span className="font-medium">{it.total_days} days from {formatDate(it.start_date)}</span></div>
                      <div className="text-xs text-muted-foreground">v{it.latest_version_number} · {it.title}</div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <div className="font-mono text-xs font-semibold">{it.enquiry_reference}</div>
                      <div className="text-xs text-muted-foreground">{it.customer_name}</div>
                    </TableCell>
                    <TableCell className="hidden max-w-md truncate text-sm lg:table-cell">{it.route.map((r) => r.city).join(" → ")}</TableCell>
                    <TableCell className="text-right">
                      <Link href={`/itineraries/${it.id}/proposal`} className={buttonVariants({ size: "sm", variant: "outline" })}><FileText aria-hidden /> Design PDF</Link>
                    </TableCell>
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
