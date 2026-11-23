"use client";

import { useState } from "react";
import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { controlClass, NativeSelect } from "@/components/common/form-controls";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { useAuth } from "@/features/auth/auth-provider";
import { EnquiriesTable } from "@/features/crm/enquiries/enquiries-table";
import { ENQUIRY_STATUS_LABELS } from "@/lib/format";
import { cn } from "@/lib/utils";
import { agentsApi, enquiriesApi, usersApi } from "@/services/crm";
import { ENQUIRY_STATUSES } from "@/types/crm";

const PAGE_SIZE = 20;

export function EnquiriesList() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [agentId, setAgentId] = useState("");
  const [planner, setPlanner] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const reset = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(1);
  };

  const params = { q, status, travel_agent_id: agentId, assigned_planner_id: planner, date_from: dateFrom, date_to: dateTo, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["enquiries", "list", params], queryFn: () => enquiriesApi.list(params), placeholderData: keepPreviousData });
  const agents = useQuery({ queryKey: ["agents", "list", { page_size: 100 }], queryFn: () => agentsApi.list({ page_size: 100 }) });
  const planners = useQuery({ queryKey: ["users", "assignable"], queryFn: usersApi.assignable });
  const filtered = Boolean(q || status || agentId || planner || dateFrom || dateTo);

  const newButton = (
    <Link href="/crm/enquiries/new" className={buttonVariants()}>
      <Plus aria-hidden /> New enquiry
    </Link>
  );

  return (
    <>
      <PageHeader title="Enquiries" description="Every incoming request from a travel agent, from first contact to confirmed booking." actions={newButton} />

      <div role="tablist" aria-label="Filter by status" className="-mx-1 mb-4 flex gap-1 overflow-x-auto px-1 pb-1">
        {["", ...ENQUIRY_STATUSES].map((s) => (
          <button
            key={s || "all"}
            role="tab"
            aria-selected={status === s}
            onClick={() => reset(setStatus)(s)}
            className={cn(
              "shrink-0 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors",
              status === s ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground ring-1 ring-border hover:text-foreground",
            )}
          >
            {s ? ENQUIRY_STATUS_LABELS[s as keyof typeof ENQUIRY_STATUS_LABELS] : "All"}
          </button>
        ))}
      </div>

      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex flex-col gap-3 xl:flex-row xl:items-center">
          <SearchInput value={q} onChange={reset(setQ)} placeholder="Reference, customer, agent, destination" label="Search enquiries" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:flex">
            <NativeSelect aria-label="Filter by travel agent" value={agentId} onChange={(e) => reset(setAgentId)(e.target.value)} className="xl:w-48">
              <option value="">All agents</option>
              {agents.data?.items.map((a) => <option key={a.id} value={a.id}>{a.company_name}</option>)}
            </NativeSelect>
            <NativeSelect aria-label="Filter by planner" value={planner} onChange={(e) => reset(setPlanner)(e.target.value)} className="xl:w-44">
              <option value="">All planners</option>
              {user && <option value={user.id}>Assigned to me</option>}
              {planners.data?.filter((p) => p.id !== user?.id).map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
            </NativeSelect>
            <input type="date" aria-label="Enquiry date from" value={dateFrom} onChange={(e) => reset(setDateFrom)(e.target.value)} className={cn(controlClass, "xl:w-40")} />
            <input type="date" aria-label="Enquiry date to" value={dateTo} onChange={(e) => reset(setDateTo)(e.target.value)} className={cn(controlClass, "xl:w-40")} />
          </div>
        </div>
        <EnquiriesTable
          query={list}
          emptyText={filtered ? "No enquiries match your filters" : "No enquiries yet"}
          emptyAction={!filtered && newButton}
        />
        {list.data && <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />}
      </Card>
    </>
  );
}
