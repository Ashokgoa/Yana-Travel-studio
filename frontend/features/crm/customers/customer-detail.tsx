"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FilePlus2, Pencil } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/common/page-header";
import { DetailItem, ErrorState, TableSkeleton } from "@/components/common/states";
import { ActiveBadge } from "@/components/common/status-badge";
import { CustomerFormDialog } from "@/features/crm/customers/customer-form-dialog";
import { travellerSummary } from "@/features/crm/customers/customers-table";
import { EnquiriesTable } from "@/features/crm/enquiries/enquiries-table";
import { formatDateTime } from "@/lib/format";
import { customersApi, enquiriesApi } from "@/services/crm";

export function CustomerDetail({ id }: { id: number }) {
  const [editing, setEditing] = useState(false);
  const customer = useQuery({ queryKey: ["customers", "detail", id], queryFn: () => customersApi.get(id) });
  const enquiries = useQuery({
    queryKey: ["enquiries", "list", { customer_id: id, page_size: 50 }],
    queryFn: () => enquiriesApi.list({ customer_id: id, page_size: 50 }),
  });

  if (customer.isPending) return <TableSkeleton rows={6} />;
  if (customer.isError) return <ErrorState message={customer.error.message} onRetry={() => customer.refetch()} />;
  const c = customer.data;
  // Direct customers (no agent) can still enquire: the agent is chosen on the enquiry form.
  const canEnquire = c.is_active && (!c.travel_agent || c.travel_agent.status === "active");
  const enquiryHref = c.travel_agent
    ? `/crm/enquiries/new?agent=${c.travel_agent.id}&customer=${c.id}`
    : `/crm/enquiries/new?customer=${c.id}`;

  return (
    <>
      <PageHeader
        back={{ href: "/crm/customers", label: "Customers" }}
        title={<span className="flex flex-wrap items-center gap-3">{c.name} <ActiveBadge status={c.is_active} /></span>}
        description={travellerSummary(c.adults, c.children)}
        actions={
          <>
            <Button variant="outline" onClick={() => setEditing(true)}>
              <Pencil aria-hidden /> Edit
            </Button>
            {canEnquire && (
              <Link href={enquiryHref} className={buttonVariants()}>
                <FilePlus2 aria-hidden /> New enquiry
              </Link>
            )}
          </>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card>
          <CardHeader>
            <CardTitle>Enquiries</CardTitle>
          </CardHeader>
          <CardContent>
            <EnquiriesTable query={enquiries} hideCustomer emptyText="No enquiries for this customer yet." />
          </CardContent>
        </Card>
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-5">
              <DetailItem label="Travel agent">
                {c.travel_agent ? (
                  <Link href={`/crm/agents/${c.travel_agent.id}`} className="text-brand-teal hover:underline">{c.travel_agent.company_name}</Link>
                ) : "Direct customer"}
              </DetailItem>
              <DetailItem label="Travellers">{travellerSummary(c.adults, c.children)}</DetailItem>
              {c.children > 0 && <DetailItem label="Children's ages">{c.children_ages.join(", ")}</DetailItem>}
              <DetailItem label="Phone">{c.phone}</DetailItem>
              <DetailItem label="Email">{c.email && <a className="text-brand-teal hover:underline" href={`mailto:${c.email}`}>{c.email}</a>}</DetailItem>
              <DetailItem label="Nationality">{c.nationality}</DetailItem>
              <DetailItem label="Country of residence">{c.country_of_residence}</DetailItem>
              <DetailItem label="Special requirements"><span className="whitespace-pre-line">{c.special_requirements}</span></DetailItem>
              <DetailItem label="Date created">{formatDateTime(c.created_at)}</DetailItem>
            </dl>
          </CardContent>
        </Card>
      </div>
      <CustomerFormDialog open={editing} onOpenChange={setEditing} customer={c} />
    </>
  );
}
