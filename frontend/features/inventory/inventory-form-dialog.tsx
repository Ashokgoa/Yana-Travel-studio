"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChipGroup, Segmented } from "@/components/common/choice-controls";
import { controlClass, FormField, FormSection, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { inventoryApi } from "@/services/inventory";
import type { InventoryItem } from "@/types/inventory";
import { CURRENCIES, humanize, type FieldDef, type ResourceConfig } from "@/features/inventory/resource-config";
import {
  type FormValue,
  type RefOption,
  toApiValue,
  toFormValue,
  useInventoryOptions,
  useRefOptions,
  validateField,
} from "@/features/inventory/use-inventory-data";

type Values = Record<string, FormValue>;

function TriStateInput({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) {
  return (
    <Segmented
      id={id}
      value={value}
      onChange={onChange}
      options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }, { value: "", label: "Unknown" }]}
    />
  );
}

function FieldInput({ field, value, onChange, error }: { field: FieldDef; value: FormValue; onChange: (v: FormValue) => void; error?: string }) {
  const { data: options } = useInventoryOptions();
  const refs = useRefOptions(field.ref);
  const id = `inv-${field.name}`;
  const aria = error ? { "aria-invalid": true as const, "aria-describedby": `${id}-error` } : {};

  const choices: RefOption[] = useMemo(() => {
    if (field.staticOptions) return field.staticOptions.map(([v, l]) => ({ value: v, label: l }));
    if (field.vocab && options) return (options[field.vocab] as string[]).map((v) => ({ value: v, label: humanize(v) }));
    return refs.data ?? [];
  }, [field, options, refs.data]);

  switch (field.type) {
    case "textarea":
      return <textarea id={id} rows={3} className={cn(controlClass, "h-auto py-2")} value={value as string} onChange={(e) => onChange(e.target.value)} {...aria} />;
    case "bool":
      return (
        <label className="flex items-start gap-2.5 text-sm">
          <input id={id} type="checkbox" className="mt-0.5 size-4 accent-[var(--brand-teal)]" checked={value as boolean} onChange={(e) => onChange(e.target.checked)} />
          <span>{field.label}</span>
        </label>
      );
    case "tristate":
      return <TriStateInput id={id} value={value as string} onChange={onChange} />;
    case "multi":
    case "multiref":
      return <ChipGroup id={id} options={choices} value={value as string[]} onChange={onChange} />;
    case "currency":
      return (
        <NativeSelect id={id} value={value as string} onChange={(e) => onChange(e.target.value)}>
          {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </NativeSelect>
      );
    case "select":
    case "reference": {
      const groups = [...new Set(choices.map((c) => c.group).filter(Boolean))] as string[];
      const renderOpt = (o: RefOption) => (
        <option key={o.value} value={o.value}>{o.label}{o.inactive ? " (inactive)" : ""}</option>
      );
      return (
        <NativeSelect id={id} value={value as string} onChange={(e) => onChange(e.target.value)} disabled={field.ref ? refs.isPending : false} {...aria}>
          <option value="">{field.ref && refs.isPending ? "Loading…" : field.required ? `Select ${field.label.toLowerCase()}` : "—"}</option>
          {groups.length
            ? groups.map((g) => <optgroup key={g} label={g}>{choices.filter((c) => c.group === g).map(renderOpt)}</optgroup>)
            : choices.map(renderOpt)}
        </NativeSelect>
      );
    }
    default:
      return (
        <input
          id={id}
          type={field.type === "email" ? "email" : "text"}
          inputMode={field.type === "int" ? "numeric" : field.type === "decimal" || field.type === "float" ? "decimal" : undefined}
          placeholder={field.placeholder}
          className={controlClass}
          value={value as string}
          onChange={(e) => onChange(e.target.value)}
          {...aria}
        />
      );
  }
}

export function InventoryFormDialog({
  config,
  open,
  onOpenChange,
  item,
  onSaved,
}: {
  config: ResourceConfig;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item?: InventoryItem;
  onSaved?: (item: InventoryItem) => void;
}) {
  // The form body remounts (fresh state from `item`) every time the dialog opens.
  const [openCount, setOpenCount] = useState(0);
  return (
    <InventoryFormBody
      key={`${openCount}-${item?.id ?? "new"}`}
      config={config}
      open={open}
      onOpenChange={(o) => {
        if (!o) setOpenCount((n) => n + 1);
        onOpenChange(o);
      }}
      item={item}
      onSaved={onSaved}
    />
  );
}

function InventoryFormBody({
  config,
  open,
  onOpenChange,
  item,
  onSaved,
}: {
  config: ResourceConfig;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item?: InventoryItem;
  onSaved?: (item: InventoryItem) => void;
}) {
  const queryClient = useQueryClient();
  const fields = config.fields.filter((f) => !f.readOnly);
  const [values, setValues] = useState<Values>(() => Object.fromEntries(fields.map((f) => [f.name, toFormValue(f, item)])) as Values);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      item ? inventoryApi.update(config.key, item.id, body) : inventoryApi.create(config.key, body),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      toast.success(`${config.singular} ${item ? "updated" : "added"}`);
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (e) => {
      if (e instanceof ApiError && e.body?.details?.length) {
        const next: Record<string, string> = {};
        const general: string[] = [];
        for (const d of e.body.details) {
          const name = d.field.split(".")[0];
          if (fields.some((f) => f.name === name)) next[name] = d.message;
          else general.push(d.message);
        }
        setErrors(next);
        if (general.length) toast.error(general.join(" "));
        else toast.error("Please correct the highlighted fields.");
      } else {
        toast.error(e instanceof ApiError ? e.message : "Could not save. Please try again.");
      }
    },
  });

  const submit = (ev: React.FormEvent) => {
    ev.preventDefault();
    const found: Record<string, string> = {};
    for (const f of fields) {
      const err = validateField(f, values[f.name]);
      if (err) found[f.name] = err;
    }
    setErrors(found);
    if (Object.keys(found).length) {
      document.getElementById(`inv-${Object.keys(found)[0]}`)?.focus();
      return;
    }
    const body: Record<string, unknown> = Object.fromEntries(fields.map((f) => [f.name, toApiValue(f, values[f.name])]));
    if (item) body.is_active = item.is_active; // status is changed with Activate/Deactivate, not the form
    mutation.mutate(body);
  };

  const sections = [...new Set(fields.map((f) => f.section))];

  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title={item ? `Edit ${config.singular.toLowerCase()}` : `New ${config.singular.toLowerCase()}`}
      description={config.description}
      formId="inventory-form"
      submitLabel={item ? "Save changes" : `Add ${config.singular.toLowerCase()}`}
      pending={mutation.isPending}
      wide
    >
      <form id="inventory-form" noValidate onSubmit={submit} className="space-y-7">
        {sections.map((section) => (
          <FormSection key={section} title={section}>
            <div className="grid gap-4 sm:grid-cols-2">
              {fields.filter((f) => f.section === section).map((f) => (
                f.type === "bool" ? (
                  <div key={f.name} className="sm:col-span-2">
                    <FieldInput field={f} value={values[f.name]} onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))} />
                    {f.hint && <p className="mt-1 ml-6.5 text-xs text-muted-foreground">{f.hint}</p>}
                  </div>
                ) : (
                  <FormField
                    key={f.name}
                    label={f.label}
                    htmlFor={`inv-${f.name}`}
                    required={f.required}
                    hint={f.hint}
                    error={errors[f.name]}
                    className={f.wide || f.type === "multi" || f.type === "multiref" ? "sm:col-span-2" : undefined}
                  >
                    <FieldInput
                      field={f}
                      value={values[f.name]}
                      error={errors[f.name]}
                      onChange={(v) => {
                        setValues((s) => ({ ...s, [f.name]: v }));
                        if (errors[f.name]) {
                          setErrors((prev) => {
                            const next = { ...prev };
                            delete next[f.name];
                            return next;
                          });
                        }
                      }}
                    />
                  </FormField>
                )
              ))}
            </div>
          </FormSection>
        ))}
      </form>
    </FormDialog>
  );
}
