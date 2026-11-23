"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { z } from "zod";
import { controlClass, errorProps, FormField, FormSection, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { emptyToNull } from "@/lib/format";
import { handleFormError } from "@/lib/form-errors";
import { agentsApi } from "@/services/crm";
import type { TravelAgent, TravelAgentInput } from "@/types/crm";

const schema = z.object({
  company_name: z.string().trim().min(1, "Company name is required").max(200),
  contact_person: z.string().max(200),
  email: z.union([z.literal(""), z.email("Enter a valid email address")]),
  phone: z.string().max(50),
  country: z.string().max(100),
  address: z.string().max(500),
  company_details: z.string(),
  internal_notes: z.string(),
  status: z.enum(["active", "inactive"]),
});
type Values = z.infer<typeof schema>;
const FIELDS = Object.keys(schema.shape);

function toValues(agent?: TravelAgent): Values {
  return {
    company_name: agent?.company_name ?? "",
    contact_person: agent?.contact_person ?? "",
    email: agent?.email ?? "",
    phone: agent?.phone ?? "",
    country: agent?.country ?? "",
    address: agent?.address ?? "",
    company_details: agent?.company_details ?? "",
    internal_notes: agent?.internal_notes ?? "",
    status: agent?.status ?? "active",
  };
}

function toInput(v: Values): TravelAgentInput {
  return {
    company_name: v.company_name.trim(),
    contact_person: emptyToNull(v.contact_person),
    email: emptyToNull(v.email),
    phone: emptyToNull(v.phone),
    country: emptyToNull(v.country),
    address: emptyToNull(v.address),
    company_details: emptyToNull(v.company_details),
    internal_notes: emptyToNull(v.internal_notes),
    status: v.status,
  };
}

export function AgentFormDialog({
  open,
  onOpenChange,
  agent,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent?: TravelAgent;
  onSaved?: (agent: TravelAgent) => void;
}) {
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, setError, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: toValues(agent),
  });
  const { errors } = formState;

  useEffect(() => {
    if (open) reset(toValues(agent));
  }, [open, agent, reset]);

  const mutation = useMutation({
    mutationFn: (input: TravelAgentInput) => (agent ? agentsApi.update(agent.id, input) : agentsApi.create(input)),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(agent ? "Travel agent updated" : "Travel agent added");
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (e) => handleFormError(e, setError, FIELDS),
  });

  const field = (name: keyof Values) => ({ id: `agent-${name}`, ...errorProps(`agent-${name}`, errors[name]?.message), ...register(name) });

  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title={agent ? "Edit travel agent" : "New travel agent"}
      description="Travel agencies and tour operators who send enquiries to YANA DMC."
      formId="agent-form"
      submitLabel={agent ? "Save changes" : "Add travel agent"}
      pending={mutation.isPending}
      wide
    >
      <form id="agent-form" noValidate onSubmit={handleSubmit((v) => mutation.mutate(toInput(v)))} className="space-y-6">
        <FormSection title="Company">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Agent / company name" htmlFor="agent-company_name" required error={errors.company_name?.message} className="sm:col-span-2">
              <input className={controlClass} autoFocus {...field("company_name")} />
            </FormField>
            <FormField label="Country" htmlFor="agent-country" error={errors.country?.message}>
              <input className={controlClass} placeholder="e.g. India" {...field("country")} />
            </FormField>
            <FormField label="Status" htmlFor="agent-status">
              <NativeSelect {...field("status")}>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </NativeSelect>
            </FormField>
            <FormField label="Address" htmlFor="agent-address" error={errors.address?.message} className="sm:col-span-2">
              <input className={controlClass} {...field("address")} />
            </FormField>
          </div>
        </FormSection>
        <FormSection title="Contact">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Contact person" htmlFor="agent-contact_person" error={errors.contact_person?.message} className="sm:col-span-2">
              <input className={controlClass} {...field("contact_person")} />
            </FormField>
            <FormField label="Email" htmlFor="agent-email" error={errors.email?.message}>
              <input type="email" className={controlClass} {...field("email")} />
            </FormField>
            <FormField label="Phone" htmlFor="agent-phone" error={errors.phone?.message}>
              <input type="tel" className={controlClass} {...field("phone")} />
            </FormField>
          </div>
        </FormSection>
        <FormSection title="Details">
          <FormField label="Company details" htmlFor="agent-company_details" hint="Registration, markets served, preferred products…">
            <textarea rows={3} className={`${controlClass} h-auto py-2`} {...field("company_details")} />
          </FormField>
          <FormField label="Internal notes" htmlFor="agent-internal_notes" hint="Visible to YANA staff only.">
            <textarea rows={3} className={`${controlClass} h-auto py-2`} {...field("internal_notes")} />
          </FormField>
        </FormSection>
      </form>
    </FormDialog>
  );
}
