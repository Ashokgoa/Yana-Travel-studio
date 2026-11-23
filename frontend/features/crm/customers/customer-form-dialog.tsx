"use client";

import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { z } from "zod";
import { controlClass, errorProps, FormField, FormSection, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { emptyToNull } from "@/lib/format";
import { handleFormError } from "@/lib/form-errors";
import { agentsApi, customersApi } from "@/services/crm";
import type { Customer, CustomerInput } from "@/types/crm";

const count = (label: string) =>
  z.string().trim().regex(/^\d+$/, `${label} must be a whole number`).refine((v) => Number(v) <= 500, `${label} looks too high`);

const schema = z
  .object({
    travel_agent_id: z.string(),
    name: z.string().trim().min(1, "Customer name is required").max(200),
    phone: z.string().max(50),
    email: z.union([z.literal(""), z.email("Enter a valid email address")]),
    nationality: z.string().max(100),
    country_of_residence: z.string().max(100),
    adults: count("Adults"),
    children: count("Children"),
    children_ages: z.array(z.string().trim().regex(/^\d+$/, "Age required").refine((v) => Number(v) <= 17, "Max 17")),
    special_requirements: z.string(),
    is_active: z.enum(["true", "false"]),
  })
  .refine((v) => Number(v.adults) + Number(v.children) >= 1, { message: "At least one traveller is required", path: ["adults"] });

type Values = z.infer<typeof schema>;
const FIELDS = ["travel_agent_id", "name", "phone", "email", "nationality", "country_of_residence", "adults", "children", "children_ages", "special_requirements"];

function toValues(c?: Customer, defaultAgentId?: number): Values {
  return {
    travel_agent_id: String(c?.travel_agent_id ?? defaultAgentId ?? ""),
    name: c?.name ?? "",
    phone: c?.phone ?? "",
    email: c?.email ?? "",
    nationality: c?.nationality ?? "",
    country_of_residence: c?.country_of_residence ?? "",
    adults: String(c?.adults ?? 2),
    children: String(c?.children ?? 0),
    children_ages: (c?.children_ages ?? []).map(String),
    special_requirements: c?.special_requirements ?? "",
    is_active: c?.is_active === false ? "false" : "true",
  };
}

function toInput(v: Values): CustomerInput {
  return {
    travel_agent_id: v.travel_agent_id ? Number(v.travel_agent_id) : null,
    name: v.name.trim(),
    phone: emptyToNull(v.phone),
    email: emptyToNull(v.email),
    nationality: emptyToNull(v.nationality),
    country_of_residence: emptyToNull(v.country_of_residence),
    adults: Number(v.adults),
    children: Number(v.children),
    children_ages: v.children_ages.map(Number),
    special_requirements: emptyToNull(v.special_requirements),
    is_active: v.is_active === "true",
  };
}

export function CustomerFormDialog({
  open,
  onOpenChange,
  customer,
  defaultAgentId,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customer?: Customer;
  defaultAgentId?: number;
  onSaved?: (c: Customer) => void;
}) {
  const queryClient = useQueryClient();
  const agents = useQuery({
    queryKey: ["agents", "list", { status: "active", page_size: 100 }],
    queryFn: () => agentsApi.list({ status: "active", page_size: 100 }),
    enabled: open,
  });

  const { register, handleSubmit, reset, setError, setValue, getValues, control, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: toValues(customer, defaultAgentId),
  });
  const { errors } = formState;
  const childCount = useWatch({ control, name: "children" });

  useEffect(() => {
    if (open) reset(toValues(customer, defaultAgentId));
  }, [open, customer, defaultAgentId, reset]);

  // Re-apply the preselected agent once the agent <option>s have loaded.
  useEffect(() => {
    if (agents.data) setValue("travel_agent_id", getValues("travel_agent_id"));
  }, [agents.data, getValues, setValue]);

  // Keep one age input per child.
  useEffect(() => {
    const n = /^\d+$/.test(childCount ?? "") ? Math.min(Number(childCount), 20) : 0;
    const ages = getValues("children_ages");
    if (ages.length !== n) {
      setValue("children_ages", Array.from({ length: n }, (_, i) => ages[i] ?? ""));
    }
  }, [childCount, getValues, setValue]);
  const ages = useWatch({ control, name: "children_ages" }) ?? [];

  const mutation = useMutation({
    mutationFn: (input: CustomerInput) => (customer ? customersApi.update(customer.id, input) : customersApi.create(input)),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(customer ? "Customer updated" : "Customer added");
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (e) => handleFormError(e, setError, FIELDS),
  });

  const field = (name: Exclude<keyof Values, "children_ages">) => ({
    id: `customer-${name}`,
    ...errorProps(`customer-${name}`, errors[name]?.message),
    ...register(name),
  });

  // An inactive agent already linked to this customer must stay selectable.
  const currentAgent = customer?.travel_agent;
  const agentOptions = agents.data?.items ?? [];
  const showCurrent = currentAgent && !agentOptions.some((a) => a.id === currentAgent.id);

  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title={customer ? "Edit customer" : "New customer"}
      description="The traveller or family the travel agent is booking for."
      formId="customer-form"
      submitLabel={customer ? "Save changes" : "Add customer"}
      pending={mutation.isPending}
      wide
    >
      <form id="customer-form" noValidate onSubmit={handleSubmit((v) => mutation.mutate(toInput(v)))} className="space-y-6">
        <FormSection title="Customer">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Customer name" htmlFor="customer-name" required error={errors.name?.message} className="sm:col-span-2">
              <input className={controlClass} autoFocus placeholder="e.g. Sharma family" {...field("name")} />
            </FormField>
            <FormField label="Travel agent" htmlFor="customer-travel_agent_id" error={errors.travel_agent_id?.message} className="sm:col-span-2">
              <NativeSelect {...field("travel_agent_id")} disabled={agents.isPending}>
                <option value="">{agents.isPending ? "Loading agents…" : "No agent (direct customer)"}</option>
                {showCurrent && <option value={currentAgent.id}>{currentAgent.company_name} (inactive)</option>}
                {agentOptions.map((a) => (
                  <option key={a.id} value={a.id}>{a.company_name}</option>
                ))}
              </NativeSelect>
            </FormField>
            <FormField label="Phone" htmlFor="customer-phone" error={errors.phone?.message}>
              <input type="tel" className={controlClass} {...field("phone")} />
            </FormField>
            <FormField label="Email" htmlFor="customer-email" error={errors.email?.message}>
              <input type="email" className={controlClass} {...field("email")} />
            </FormField>
            <FormField label="Nationality" htmlFor="customer-nationality" hint="Optional">
              <input className={controlClass} {...field("nationality")} />
            </FormField>
            <FormField label="Country of residence" htmlFor="customer-country_of_residence">
              <input className={controlClass} {...field("country_of_residence")} />
            </FormField>
          </div>
        </FormSection>

        <FormSection title="Travellers">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <FormField label="Adults" htmlFor="customer-adults" required error={errors.adults?.message}>
              <input inputMode="numeric" className={controlClass} {...field("adults")} />
            </FormField>
            <FormField label="Children" htmlFor="customer-children" error={errors.children?.message}>
              <input inputMode="numeric" className={controlClass} {...field("children")} />
            </FormField>
          </div>
          {ages.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-medium">Children&apos;s ages</p>
              <div className="flex flex-wrap gap-3">
                {ages.map((_, i) => {
                  const err = errors.children_ages?.[i]?.message;
                  return (
                    <div key={i} className="w-24">
                      <label htmlFor={`child-age-${i}`} className="text-xs text-muted-foreground">Child {i + 1}</label>
                      <input
                        id={`child-age-${i}`}
                        inputMode="numeric"
                        className={controlClass}
                        aria-invalid={err ? true : undefined}
                        {...register(`children_ages.${i}` as const)}
                      />
                      {err && <p className="mt-1 text-xs text-destructive">{err}</p>}
                    </div>
                  );
                })}
              </div>
              {errors.children_ages?.message && <p className="mt-1 text-xs text-destructive">{errors.children_ages.message}</p>}
            </div>
          )}
          <FormField label="Special requirements" htmlFor="customer-special_requirements" hint="Mobility, dietary, celebrations…">
            <textarea rows={3} className={`${controlClass} h-auto py-2`} {...field("special_requirements")} />
          </FormField>
          {customer && (
            <FormField label="Status" htmlFor="customer-is_active">
              <NativeSelect {...field("is_active")} className="sm:w-48">
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </NativeSelect>
            </FormField>
          )}
        </FormSection>
      </form>
    </FormDialog>
  );
}
