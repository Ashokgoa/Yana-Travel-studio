"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, ClipboardList, Pencil, RefreshCcw } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { controlClass, FormField, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { PageHeader } from "@/components/common/page-header";
import { DetailItem, ErrorState, TableSkeleton } from "@/components/common/states";
import { EnquiryStatusBadge } from "@/components/common/status-badge";
import { travellerSummary } from "@/features/crm/customers/customers-table";
import { ENQUIRY_STATUS_LABELS, formatDate, formatDateTime, formatMoney, tripLength } from "@/lib/format";
import { handleFormError } from "@/lib/form-errors";
import { enquiriesApi, requirementsApi } from "@/services/crm";
import { ReadinessList, RequirementsSummary } from "@/features/requirements/requirements-summary";
import { EnquiryItineraries } from "@/features/itineraries/enquiry-itineraries";
import { ENQUIRY_STATUSES, type EnquiryDetail, type EnquiryStatus } from "@/types/crm";

function StatusDialog({ enquiry, open, onOpenChange }: { enquiry: EnquiryDetail; open: boolean; onOpenChange: (o: boolean) => void }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<EnquiryStatus | "">("");
  const [note, setNote] = useState("");
  const mutation = useMutation({
    mutationFn: () => enquiriesApi.changeStatus(enquiry.id, status as EnquiryStatus, note.trim() || undefined),
    onSuccess: (e) => {
      queryClient.setQueryData(["enquiries", "detail", enquiry.id], e);
      queryClient.invalidateQueries({ queryKey: ["enquiries", "list"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(`Status changed to ${ENQUIRY_STATUS_LABELS[e.status]}`);
      onOpenChange(false);
      setStatus("");
      setNote("");
    },
    onError: (e) => handleFormError(e),
  });

  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Change status"
      description={`Currently ${ENQUIRY_STATUS_LABELS[enquiry.status]}. The change is recorded in the enquiry history.`}
      formId="status-form"
      submitLabel="Update status"
      pending={mutation.isPending}
    >
      <form
        id="status-form"
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!status) {
            toast.error("Choose the new status.");
            return;
          }
          mutation.mutate();
        }}
      >
        <FormField label="New status" htmlFor="status-new" required>
          <NativeSelect id="status-new" value={status} onChange={(e) => setStatus(e.target.value as EnquiryStatus)} autoFocus>
            <option value="">Select status</option>
            {ENQUIRY_STATUSES.filter((s) => s !== enquiry.status).map((s) => (
              <option key={s} value={s}>{ENQUIRY_STATUS_LABELS[s]}</option>
            ))}
          </NativeSelect>
        </FormField>
        <FormField label="Note" htmlFor="status-note" hint="Optional, e.g. 'Agent asked for a 4★ alternative'">
          <textarea id="status-note" rows={3} maxLength={1000} className={`${controlClass} h-auto py-2`} value={note} onChange={(e) => setNote(e.target.value)} />
        </FormField>
      </form>
    </FormDialog>
  );
}

function RequirementsCard({ enquiryId }: { enquiryId: number }) {
  const req = useQuery({ queryKey: ["requirements", enquiryId], queryFn: () => requirementsApi.get(enquiryId) });
  const href = `/crm/enquiries/${enquiryId}/requirements`;
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div>
          <CardTitle>Customer requirements</CardTitle>
          {req.data?.exists && (
            <p className="mt-1 text-xs text-muted-foreground">{req.data.completed_steps.length} of 9 steps saved</p>
          )}
        </div>
        {req.data?.exists && (
          <Link href={href} className={buttonVariants({ variant: "outline", size: "sm" })}>
            <Pencil aria-hidden /> Edit
          </Link>
        )}
      </CardHeader>
      <CardContent>
        {req.isPending ? (
          <TableSkeleton rows={2} />
        ) : req.isError ? (
          <ErrorState message={req.error.message} onRetry={() => req.refetch()} />
        ) : !req.data.exists ? (
          <div className="flex flex-col items-start gap-3 rounded-xl border border-dashed p-6 sm:flex-row sm:items-center">
            <ClipboardList className="size-6 text-brand-teal" aria-hidden />
            <div className="flex-1 text-sm">
              <p className="font-medium">No detailed requirements yet</p>
              <p className="text-muted-foreground">Capture destinations, interests, hotels, food, transport and budget in 9 short steps.</p>
            </div>
            <Link href={href} className={buttonVariants()}>Capture requirements</Link>
          </div>
        ) : (
          <div className="space-y-5">
            <RequirementsSummary req={req.data} />
            <div className="rounded-xl border bg-muted/20 p-4"><ReadinessList req={req.data} /></div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function EnquiryDetailView({ id }: { id: number }) {
  const [changingStatus, setChangingStatus] = useState(false);
  const query = useQuery({ queryKey: ["enquiries", "detail", id], queryFn: () => enquiriesApi.get(id) });

  if (query.isPending) return <TableSkeleton rows={6} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const e = query.data;
  const length = tripLength(e.travel_start_date, e.travel_end_date);
  const history = [...e.status_history].reverse();

  return (
    <>
      <PageHeader
        back={{ href: "/crm/enquiries", label: "Enquiries" }}
        title={
          <span className="flex flex-wrap items-center gap-3">
            <span className="font-mono text-2xl">{e.reference}</span>
            <EnquiryStatusBadge status={e.status} />
          </span>
        }
        description={`${e.customer.name} · via ${e.travel_agent.company_name}`}
        actions={
          <>
            <Link href={`/crm/enquiries/${e.id}/edit`} className={buttonVariants({ variant: "outline" })}>
              <Pencil aria-hidden /> Edit
            </Link>
            <Button onClick={() => setChangingStatus(true)}>
              <RefreshCcw aria-hidden /> Change status
            </Button>
          </>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Trip summary</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                <DetailItem label="Travel dates">
                  {e.travel_start_date ? `${formatDate(e.travel_start_date)} – ${formatDate(e.travel_end_date)}` : null}
                </DetailItem>
                <DetailItem label="Duration">{length ? `${length.days} days / ${length.nights} nights` : null}</DetailItem>
                <DetailItem label="Travellers">{travellerSummary(e.adults, e.children)}</DetailItem>
                <DetailItem label="Budget">
                  {e.budget_amount
                    ? `${formatMoney(e.budget_amount, e.budget_currency)} ${e.budget_basis === "per_person" ? "per person" : "group total"}`
                    : null}
                </DetailItem>
                <DetailItem label="Enquiry date">{formatDate(e.enquiry_date)}</DetailItem>
                <DetailItem label="Assigned planner">{e.assigned_planner?.full_name ?? "Unassigned"}</DetailItem>
                <div className="sm:col-span-2 lg:col-span-3">
                  <DetailItem label="Destination preferences">
                    <span className="whitespace-pre-line">{e.destination_preferences}</span>
                  </DetailItem>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Internal comments</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm whitespace-pre-line">
                {e.internal_comments || <span className="text-muted-foreground">No internal comments.</span>}
              </p>
            </CardContent>
          </Card>

          <RequirementsCard enquiryId={e.id} />
          <EnquiryItineraries enquiryId={e.id} />
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>People</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-5">
                <DetailItem label="Travel agent">
                  <Link href={`/crm/agents/${e.travel_agent.id}`} className="text-brand-teal hover:underline">{e.travel_agent.company_name}</Link>
                </DetailItem>
                <DetailItem label="Customer">
                  <Link href={`/crm/customers/${e.customer.id}`} className="text-brand-teal hover:underline">{e.customer.name}</Link>
                </DetailItem>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Status history</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="relative space-y-5 border-l pl-5">
                {history.map((h) => (
                  <li key={h.id} className="relative">
                    <span className="absolute top-1.5 -left-[25px] size-2.5 rounded-full bg-brand-teal ring-4 ring-card" aria-hidden />
                    <div className="flex flex-wrap items-center gap-1.5 text-sm">
                      {h.from_status && (
                        <>
                          <span className="text-muted-foreground">{ENQUIRY_STATUS_LABELS[h.from_status]}</span>
                          <ArrowRight className="size-3 text-muted-foreground" aria-label="to" />
                        </>
                      )}
                      <span className="font-medium">{ENQUIRY_STATUS_LABELS[h.to_status]}</span>
                    </div>
                    {h.note && <p className="mt-1 text-sm whitespace-pre-line">{h.note}</p>}
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateTime(h.created_at)}
                      {h.changed_by && ` · ${h.changed_by.full_name}`}
                    </p>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </div>
      </div>

      <StatusDialog enquiry={e} open={changingStatus} onOpenChange={setChangingStatus} />
    </>
  );
}
