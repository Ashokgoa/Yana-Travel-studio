"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/common/form-controls";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { CustomerFormDialog } from "@/features/crm/customers/customer-form-dialog";
import { CustomersTable } from "@/features/crm/customers/customers-table";
import { agentsApi, customersApi } from "@/services/crm";

const PAGE_SIZE = 20;

export function CustomersList() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [agentId, setAgentId] = useState("");
  const [active, setActive] = useState("true");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);

  const params = { q, travel_agent_id: agentId, active, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["customers", "list", params], queryFn: () => customersApi.list(params), placeholderData: keepPreviousData });
  const agents = useQuery({ queryKey: ["agents", "list", { page_size: 100 }], queryFn: () => agentsApi.list({ page_size: 100 }) });
  const filtered = Boolean(q || agentId);

  return (
    <>
      <PageHeader
        title="Customers"
        description="Travellers and families linked to your travel agents."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus aria-hidden /> New customer
          </Button>
        }
      />
      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Search name, email, phone" label="Search customers" />
          <div className="grid grid-cols-2 gap-3 sm:flex">
            <NativeSelect aria-label="Filter by travel agent" value={agentId} onChange={(e) => { setAgentId(e.target.value); setPage(1); }} className="sm:w-56">
              <option value="">All travel agents</option>
              {agents.data?.items.map((a) => (
                <option key={a.id} value={a.id}>{a.company_name}</option>
              ))}
            </NativeSelect>
            <NativeSelect aria-label="Filter by status" value={active} onChange={(e) => { setActive(e.target.value); setPage(1); }} className="sm:w-36">
              <option value="true">Active</option>
              <option value="false">Inactive</option>
              <option value="">All</option>
            </NativeSelect>
          </div>
        </div>
        <CustomersTable
          query={list}
          emptyText={filtered ? "No customers match your filters" : "No customers yet"}
          emptyAction={!filtered && <Button onClick={() => setCreating(true)}><Plus aria-hidden /> New customer</Button>}
        />
        {list.data && <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />}
      </Card>
      <CustomerFormDialog open={creating} onOpenChange={setCreating} onSaved={(c) => router.push(`/crm/customers/${c.id}`)} />
    </>
  );
}
