"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { NativeSelect } from "@/components/common/form-controls";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { ActiveBadge } from "@/components/common/status-badge";
import { AgentFormDialog } from "@/features/crm/agents/agent-form-dialog";
import { agentsApi } from "@/services/crm";

const PAGE_SIZE = 20;

export function AgentsList() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [country, setCountry] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);

  const params = { q, status, country, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["agents", "list", params], queryFn: () => agentsApi.list(params), placeholderData: keepPreviousData });
  const countries = useQuery({ queryKey: ["agents", "countries"], queryFn: agentsApi.countries });
  const filtered = Boolean(q || status || country);

  return (
    <>
      <PageHeader
        title="Travel Agents"
        description="Agencies and tour operators who send enquiries to YANA DMC."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus aria-hidden /> New travel agent
          </Button>
        }
      />

      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <SearchInput
            value={q}
            onChange={(v) => {
              setQ(v);
              setPage(1);
            }}
            placeholder="Search name, contact, email, phone"
            label="Search travel agents"
          />
          <div className="grid grid-cols-2 gap-3 sm:flex">
            <NativeSelect aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="sm:w-40">
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </NativeSelect>
            <NativeSelect aria-label="Filter by country" value={country} onChange={(e) => { setCountry(e.target.value); setPage(1); }} className="sm:w-44">
              <option value="">All countries</option>
              {countries.data?.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </NativeSelect>
          </div>
        </div>

        {list.isPending ? (
          <TableSkeleton />
        ) : list.isError ? (
          <ErrorState message={list.error.message} onRetry={() => list.refetch()} />
        ) : list.data.items.length === 0 ? (
          <EmptyState
            icon={Building2}
            title={filtered ? "No travel agents match your filters" : "No travel agents yet"}
            description={filtered ? "Try a different search or clear the filters." : "Add the agencies you work with to start logging enquiries."}
            action={!filtered && <Button onClick={() => setCreating(true)}><Plus aria-hidden /> New travel agent</Button>}
          />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent / company</TableHead>
                  <TableHead className="hidden md:table-cell">Contact</TableHead>
                  <TableHead className="hidden sm:table-cell">Country</TableHead>
                  <TableHead className="hidden lg:table-cell text-right">Customers</TableHead>
                  <TableHead className="hidden lg:table-cell text-right">Enquiries</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((a) => (
                  <TableRow key={a.id} className="cursor-pointer" onClick={() => router.push(`/crm/agents/${a.id}`)}>
                    <TableCell className="font-medium">
                      <Link href={`/crm/agents/${a.id}`} className="hover:underline" onClick={(e) => e.stopPropagation()}>
                        {a.company_name}
                      </Link>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <div>{a.contact_person ?? "—"}</div>
                      <div className="text-xs text-muted-foreground">{a.email ?? a.phone ?? ""}</div>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">{a.country ?? "—"}</TableCell>
                    <TableCell className="hidden lg:table-cell text-right tabular-nums">{a.customer_count}</TableCell>
                    <TableCell className="hidden lg:table-cell text-right tabular-nums">{a.enquiry_count}</TableCell>
                    <TableCell><ActiveBadge status={a.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />
          </>
        )}
      </Card>

      <AgentFormDialog open={creating} onOpenChange={setCreating} onSaved={(a) => router.push(`/crm/agents/${a.id}`)} />
    </>
  );
}
