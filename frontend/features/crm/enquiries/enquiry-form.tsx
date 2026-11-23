"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { z } from "zod";
import { CalendarRange, Loader2, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { controlClass, errorProps, FormField, FormSection, NativeSelect } from "@/components/common/form-controls";
import { useAuth } from "@/features/auth/auth-provider";
import { CustomerFormDialog } from "@/features/crm/customers/customer-form-dialog";
import { emptyToNull, todayIso, tripLength } from "@/lib/format";
import { handleFormError } from "@/lib/form-errors";
import { agentsApi, customersApi, enquiriesApi, usersApi } from "@/services/crm";
import type { EnquiryDetail, EnquiryInput } from "@/types/crm";

export const CURRENCIES = ["EUR", "GBP", "USD", "CHF", "INR", "AED"];
const wholeNumber = (label: string) => z.string().trim().regex(/^\d+$/, `${label} must be a whole number`);

const schema = z
  .object({
    travel_agent_id: z.string().min(1, "Select a travel agent"),
    customer_id: z.string().min(1, "Select a customer"),
    enquiry_date: z.string().min(1, "Enquiry date is required"),
    travel_start_date: z.string(),
    travel_end_date: z.string(),
    adults: wholeNumber("Adults"),
    children: wholeNumber("Children"),
    destination_preferences: z.string(),
    budget_amount: z.union([z.literal(""), z.string().trim().regex(/^\d+(\.\d{1,2})?$/, "Enter an amount, e.g. 3000")]),
    budget_currency: z.string().length(3),
    budget_basis: z.enum(["", "per_person", "total"]),
    assigned_planner_id: z.string(),
    internal_comments: z.string(),
  })
  .refine((v) => Number(v.adults) + Number(v.children) >= 1, { message: "At least one traveller is required", path: ["adults"] })
  .refine((v) => !v.travel_start_date || !v.travel_end_date || v.travel_end_date >= v.travel_start_date, {
    message: "End date cannot be before the start date",
    path: ["travel_end_date"],
  })
  .refine((v) => !v.budget_amount || v.budget_basis !== "", { message: "Choose per person or group total", path: ["budget_basis"] });

type Values = z.infer<typeof schema>;
const FIELDS: (keyof Values)[] = [
  "travel_agent_id", "customer_id", "enquiry_date", "travel_start_date", "travel_end_date", "adults", "children",
  "destination_preferences", "budget_amount", "budget_currency", "budget_basis", "assigned_planner_id", "internal_comments",
];

function toValues(e?: EnquiryDetail, defaults?: Partial<Values>): Values {
  return {
    travel_agent_id: e ? String(e.travel_agent_id) : defaults?.travel_agent_id ?? "",
    customer_id: e ? String(e.customer_id) : defaults?.customer_id ?? "",
    enquiry_date: e?.enquiry_date ?? todayIso(),
    travel_start_date: e?.travel_start_date ?? "",
    travel_end_date: e?.travel_end_date ?? "",
    adults: String(e?.adults ?? 2),
    children: String(e?.children ?? 0),
    destination_preferences: e?.destination_preferences ?? "",
    budget_amount: e?.budget_amount ? String(Number(e.budget_amount)) : "",
    budget_currency: e?.budget_currency ?? "EUR",
    budget_basis: e?.budget_basis ?? "",
    assigned_planner_id: e ? String(e.assigned_planner_id ?? "") : defaults?.assigned_planner_id ?? "",
    internal_comments: e?.internal_comments ?? "",
  };
}

function toInput(v: Values): EnquiryInput {
  return {
    travel_agent_id: Number(v.travel_agent_id),
    customer_id: Number(v.customer_id),
    enquiry_date: v.enquiry_date,
    travel_start_date: v.travel_start_date || null,
    travel_end_date: v.travel_end_date || null,
    adults: Number(v.adults),
    children: Number(v.children),
    destination_preferences: emptyToNull(v.destination_preferences),
    budget_amount: v.budget_amount || null,
    budget_currency: v.budget_currency,
    budget_basis: v.budget_basis || null,
    assigned_planner_id: v.assigned_planner_id ? Number(v.assigned_planner_id) : null,
    internal_comments: emptyToNull(v.internal_comments),
  };
}

/** Create (no `enquiry`) or edit an enquiry. Prefills agent/customer from ?agent=&customer=. */
export function EnquiryForm({ enquiry }: { enquiry?: EnquiryDetail }) {
  const router = useRouter();
  const search = useSearchParams();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [addingCustomer, setAddingCustomer] = useState(false);

  const { register, handleSubmit, setValue, setError, control, getValues, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: toValues(enquiry, {
      travel_agent_id: search.get("agent") ?? "",
      customer_id: search.get("customer") ?? "",
      assigned_planner_id: user ? String(user.id) : "",
    }),
  });
  const { errors } = formState;
  const [agentId, customerId, start, end] = useWatch({ control, name: ["travel_agent_id", "customer_id", "travel_start_date", "travel_end_date"] });
  const length = tripLength(start || null, end || null);

  const agents = useQuery({
    queryKey: ["agents", "list", { status: "active", page_size: 100 }],
    queryFn: () => agentsApi.list({ status: "active", page_size: 100 }),
  });
  const customers = useQuery({
    queryKey: ["customers", "list", { travel_agent_id: agentId, active: true, page_size: 100 }],
    queryFn: () => customersApi.list({ travel_agent_id: agentId, active: true, page_size: 100 }),
    enabled: Boolean(agentId),
  });
  // A direct customer (no agent) arriving via ?customer= must be selectable too.
  const preselected = useQuery({
    queryKey: ["customers", "detail", Number(customerId)],
    queryFn: () => customersApi.get(Number(customerId)),
    enabled: Boolean(customerId),
  });
  const planners = useQuery({ queryKey: ["users", "assignable"], queryFn: usersApi.assignable });

  // Native <select>s drop a preset value whose <option> hasn't loaded yet; re-apply
  // the form value once each option list arrives (prefills from URL / current user).
  useEffect(() => {
    if (agents.data) setValue("travel_agent_id", getValues("travel_agent_id"));
  }, [agents.data, getValues, setValue]);
  useEffect(() => {
    if (customers.data || preselected.data) setValue("customer_id", getValues("customer_id"));
  }, [customers.data, preselected.data, getValues, setValue]);
  useEffect(() => {
    if (planners.data) setValue("assigned_planner_id", getValues("assigned_planner_id"));
  }, [planners.data, getValues, setValue]);

  // When a new customer is picked, copy their traveller numbers (planner can still adjust).
  useEffect(() => {
    const c = preselected.data;
    if (!c || enquiry) return;
    if (String(c.id) !== getValues("customer_id")) return;
    setValue("adults", String(c.adults));
    setValue("children", String(c.children));
  }, [preselected.data, enquiry, getValues, setValue]);

  const customerOptions = [...(customers.data?.items ?? [])];
  const pre = preselected.data;
  if (pre && !pre.travel_agent_id && !customerOptions.some((c) => c.id === pre.id)) customerOptions.unshift(pre);

  const mutation = useMutation({
    mutationFn: (input: EnquiryInput) => (enquiry ? enquiriesApi.update(enquiry.id, input) : enquiriesApi.create(input)),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["enquiries"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      toast.success(enquiry ? "Enquiry updated" : `Enquiry ${saved.reference} created`);
      router.push(`/crm/enquiries/${saved.id}`);
    },
    onError: (e) => handleFormError(e, setError, FIELDS),
  });

  const field = (name: keyof Values) => ({ id: `enq-${name}`, ...errorProps(`enq-${name}`, errors[name]?.message), ...register(name) });

  return (
    <form noValidate onSubmit={handleSubmit((v) => mutation.mutate(toInput(v)))}>
      <Card>
        <CardContent className="space-y-8 pt-6">
          <FormSection title="Who is enquiring">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Travel agent" htmlFor="enq-travel_agent_id" required error={errors.travel_agent_id?.message}>
                <NativeSelect
                  {...field("travel_agent_id")}
                  onChange={(e) => {
                    register("travel_agent_id").onChange(e);
                    const keep = pre && !pre.travel_agent_id && String(pre.id) === getValues("customer_id");
                    if (!keep) setValue("customer_id", "");
                  }}
                >
                  <option value="">{agents.isPending ? "Loading…" : "Select travel agent"}</option>
                  {enquiry && !agents.data?.items.some((a) => a.id === enquiry.travel_agent_id) && (
                    <option value={enquiry.travel_agent_id}>{enquiry.travel_agent.company_name} (inactive)</option>
                  )}
                  {agents.data?.items.map((a) => <option key={a.id} value={a.id}>{a.company_name}</option>)}
                </NativeSelect>
              </FormField>
              <FormField label="Customer" htmlFor="enq-customer_id" required error={errors.customer_id?.message}>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <NativeSelect {...field("customer_id")} disabled={!agentId}>
                      <option value="">{!agentId ? "Select an agent first" : customers.isPending ? "Loading…" : "Select customer"}</option>
                      {customerOptions.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </NativeSelect>
                  </div>
                  <Button type="button" variant="outline" className="h-10" disabled={!agentId} onClick={() => setAddingCustomer(true)} aria-label="Add new customer">
                    <UserPlus aria-hidden />
                  </Button>
                </div>
              </FormField>
              <FormField label="Enquiry date" htmlFor="enq-enquiry_date" required error={errors.enquiry_date?.message}>
                <input type="date" className={controlClass} {...field("enquiry_date")} />
              </FormField>
              <FormField label="Assigned planner" htmlFor="enq-assigned_planner_id">
                <NativeSelect {...field("assigned_planner_id")}>
                  <option value="">Unassigned</option>
                  {planners.data?.map((p) => <option key={p.id} value={p.id}>{p.full_name}{p.id === user?.id ? " (me)" : ""}</option>)}
                </NativeSelect>
              </FormField>
            </div>
          </FormSection>

          <FormSection title="Trip" description="High-level details. Full requirements (countries, hotels, food, transport) are captured in Phase 3.">
            <div className="grid gap-4 sm:grid-cols-4">
              <FormField label="Travel from" htmlFor="enq-travel_start_date" error={errors.travel_start_date?.message} className="sm:col-span-2">
                <input type="date" className={controlClass} {...field("travel_start_date")} />
              </FormField>
              <FormField label="Travel to" htmlFor="enq-travel_end_date" error={errors.travel_end_date?.message} className="sm:col-span-2">
                <input type="date" className={controlClass} min={start || undefined} {...field("travel_end_date")} />
              </FormField>
              {length && (
                <p className="flex items-center gap-2 text-sm text-muted-foreground sm:col-span-4">
                  <CalendarRange className="size-4 text-brand-teal" aria-hidden />
                  {length.days} days / {length.nights} nights
                </p>
              )}
              <FormField label="Adults" htmlFor="enq-adults" required error={errors.adults?.message}>
                <input inputMode="numeric" className={controlClass} {...field("adults")} />
              </FormField>
              <FormField label="Children" htmlFor="enq-children" error={errors.children?.message}>
                <input inputMode="numeric" className={controlClass} {...field("children")} />
              </FormField>
              <FormField label="Destination preferences" htmlFor="enq-destination_preferences" className="sm:col-span-4" hint="e.g. Amsterdam, Paris and Switzerland; arrive AMS, depart ZRH">
                <textarea rows={3} className={`${controlClass} h-auto py-2`} {...field("destination_preferences")} />
              </FormField>
            </div>
          </FormSection>

          <FormSection title="Budget">
            <div className="grid gap-4 sm:grid-cols-4">
              <FormField label="Amount" htmlFor="enq-budget_amount" error={errors.budget_amount?.message} className="sm:col-span-2">
                <input inputMode="decimal" className={controlClass} placeholder="e.g. 3000" {...field("budget_amount")} />
              </FormField>
              <FormField label="Currency" htmlFor="enq-budget_currency">
                <NativeSelect {...field("budget_currency")}>
                  {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </NativeSelect>
              </FormField>
              <FormField label="Basis" htmlFor="enq-budget_basis" error={errors.budget_basis?.message}>
                <NativeSelect {...field("budget_basis")}>
                  <option value="">—</option>
                  <option value="per_person">Per person</option>
                  <option value="total">Group total</option>
                </NativeSelect>
              </FormField>
            </div>
          </FormSection>

          <FormSection title="Internal">
            <FormField label="Internal comments" htmlFor="enq-internal_comments" hint="Visible to YANA staff only; never shown to agents or customers.">
              <textarea rows={3} className={`${controlClass} h-auto py-2`} {...field("internal_comments")} />
            </FormField>
          </FormSection>
        </CardContent>
        <div className="flex justify-end gap-2 border-t px-6 py-4">
          <Button type="button" variant="outline" onClick={() => router.back()} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" aria-hidden />}
            {enquiry ? "Save changes" : "Create enquiry"}
          </Button>
        </div>
      </Card>

      <CustomerFormDialog
        open={addingCustomer}
        onOpenChange={setAddingCustomer}
        defaultAgentId={agentId ? Number(agentId) : undefined}
        onSaved={(c) => {
          setValue("customer_id", String(c.id), { shouldValidate: true });
          setValue("adults", String(c.adults));
          setValue("children", String(c.children));
        }}
      />
    </form>
  );
}
