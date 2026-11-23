"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FilePlus2, Pencil, Power, UserPlus } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PageHeader } from "@/components/common/page-header";
import { DetailItem, ErrorState, TableSkeleton } from "@/components/common/states";
import { ActiveBadge } from "@/components/common/status-badge";
import { AgentFormDialog } from "@/features/crm/agents/agent-form-dialog";
import { CustomerFormDialog } from "@/features/crm/customers/customer-form-dialog";
import { CustomersTable } from "@/features/crm/customers/customers-table";
import { EnquiriesTable } from "@/features/crm/enquiries/enquiries-table";
import { formatDateTime } from "@/lib/format";
import { handleFormError } from "@/lib/form-errors";
import { agentsApi, customersApi, enquiriesApi } from "@/services/crm";

export function AgentDetail({ id }: { id: number }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [addingCustomer, setAddingCustomer] = useState(false);
  const [confirmStatus, setConfirmStatus] = useState(false);

  const agent = useQuery({ queryKey: ["agents", "detail", id], queryFn: () => agentsApi.get(id) });
  const customers = useQuery({
    queryKey: ["customers", "list", { travel_agent_id: id, page_size: 100 }],
    queryFn: () => customersApi.list({ travel_agent_id: id, page_size: 100 }),
  });
  const enquiries = useQuery({
    queryKey: ["enquiries", "list", { travel_agent_id: id, page_size: 10 }],
    queryFn: () => enquiriesApi.list({ travel_agent_id: id, page_size: 10 }),
  });

  const toggle = useMutation({
    mutationFn: () => agentsApi.setStatus(id, agent.data?.status === "active" ? "inactive" : "active"),
    onSuccess: (a) => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(a.status === "active" ? "Travel agent reactivated" : "Travel agent deactivated");
      setConfirmStatus(false);
    },
    onError: (e) => handleFormError(e),
  });

  if (agent.isPending) return <TableSkeleton rows={6} />;
  if (agent.isError) return <ErrorState message={agent.error.message} onRetry={() => agent.refetch()} />;
  const a = agent.data;
  const active = a.status === "active";

  return (
    <>
      <PageHeader
        back={{ href: "/crm/agents", label: "Travel agents" }}
        title={<span className="flex flex-wrap items-center gap-3">{a.company_name} <ActiveBadge status={a.status} /></span>}
        description={[a.country, a.contact_person].filter(Boolean).join(" · ") || undefined}
        actions={
          <>
            <Button variant="outline" onClick={() => setConfirmStatus(true)}>
              <Power aria-hidden /> {active ? "Deactivate" : "Reactivate"}
            </Button>
            <Button variant="outline" onClick={() => setEditing(true)}>
              <Pencil aria-hidden /> Edit
            </Button>
            {active && (
              <Link href={`/crm/enquiries/new?agent=${a.id}`} className={buttonVariants()}>
                <FilePlus2 aria-hidden /> New enquiry
              </Link>
            )}
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Customers ({customers.data?.total ?? "…"})</CardTitle>
              {active && (
                <Button size="sm" variant="outline" onClick={() => setAddingCustomer(true)}>
                  <UserPlus aria-hidden /> Add customer
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <CustomersTable query={customers} hideAgent emptyText="No customers for this agent yet." />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Recent enquiries</CardTitle>
            </CardHeader>
            <CardContent>
              <EnquiriesTable query={enquiries} hideAgent emptyText="No enquiries from this agent yet." />
            </CardContent>
          </Card>
        </div>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-5">
              <DetailItem label="Contact person">{a.contact_person}</DetailItem>
              <DetailItem label="Email">{a.email && <a className="text-brand-teal hover:underline" href={`mailto:${a.email}`}>{a.email}</a>}</DetailItem>
              <DetailItem label="Phone">{a.phone}</DetailItem>
              <DetailItem label="Country">{a.country}</DetailItem>
              <DetailItem label="Address">{a.address}</DetailItem>
              <DetailItem label="Company details"><span className="whitespace-pre-line">{a.company_details}</span></DetailItem>
              <DetailItem label="Internal notes"><span className="whitespace-pre-line">{a.internal_notes}</span></DetailItem>
              <DetailItem label="Date created">{formatDateTime(a.created_at)}</DetailItem>
            </dl>
          </CardContent>
        </Card>
      </div>

      <AgentFormDialog open={editing} onOpenChange={setEditing} agent={a} />
      <CustomerFormDialog open={addingCustomer} onOpenChange={setAddingCustomer} defaultAgentId={a.id} />
      <ConfirmDialog
        open={confirmStatus}
        onOpenChange={setConfirmStatus}
        title={active ? `Deactivate ${a.company_name}?` : `Reactivate ${a.company_name}?`}
        description={
          active
            ? "Inactive agents stay on record with their history, but new customers and enquiries can't be created for them."
            : "The agent will be available again for new customers and enquiries."
        }
        confirmLabel={active ? "Deactivate" : "Reactivate"}
        destructive={active}
        pending={toggle.isPending}
        onConfirm={() => toggle.mutate()}
      />
    </>
  );
}
