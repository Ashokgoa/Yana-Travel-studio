"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { FormField, NativeSelect, controlClass } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/lib/format";
import { ApiError } from "@/services/api";
import { pricingApi } from "@/services/pricing";
import { BASIS_LABELS, CATEGORIES, CATEGORY_LABELS, type PricingBasis, type PricingCategory, type SupplierRate, type SupplierRateInput } from "@/types/pricing";
import { money } from "./pricing-parts-shared";

const TYPE_TO_CATEGORY: Record<string, PricingCategory> = { hotel: "hotel", coach: "transport", restaurant: "meal", guide: "guide", attraction: "sightseeing", other: "other" };
const CURRENCIES = ["EUR", "CHF", "GBP", "USD", "SEK", "NOK", "DKK", "CZK", "HUF", "PLN", "INR"];

function season(r: { valid_from: string | null; valid_to: string | null }) {
  if (!r.valid_from && !r.valid_to) return "All year";
  return `${r.valid_from ? formatDate(r.valid_from) : "…"} – ${r.valid_to ? formatDate(r.valid_to) : "…"}`;
}

/** A supplier's rate card: prices per service, optionally per season. Used to fill supplier prices on pricing sheets. */
export function SupplierRates({ supplierId, supplierType }: { supplierId: number; supplierType: string }) {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["supplier-rates", "card", supplierId], queryFn: () => pricingApi.supplierRates(supplierId) });
  const [editing, setEditing] = useState<SupplierRate | "new" | null>(null);
  const del = useMutation({
    mutationFn: (rid: number) => pricingApi.deleteRate(rid),
    onSuccess: () => { toast.success("Rate removed"); void qc.invalidateQueries({ queryKey: ["supplier-rates"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not remove"),
  });
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <div>
          <CardTitle className="text-base">Rate card</CardTitle>
          <p className="text-xs text-muted-foreground">This supplier&apos;s prices. They pop up when you enter a supplier price on a pricing sheet; you can still change them there.</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setEditing("new")}><Plus aria-hidden /> Add rate</Button>
      </CardHeader>
      <CardContent>
        {list.isPending ? <p className="text-sm text-muted-foreground">Loading…</p> : !list.data?.length ? (
          <p className="text-sm text-muted-foreground">No rates yet.</p>
        ) : (
          <table className="w-full text-sm" aria-label="Rate card">
            <thead className="text-left text-xs text-muted-foreground">
              <tr><th className="py-1 font-medium">Service</th><th className="font-medium">Basis</th><th className="font-medium">Season</th><th className="text-right font-medium">Price</th><th className="w-16" /></tr>
            </thead>
            <tbody>
              {list.data.map((r) => (
                <tr key={r.id} className={r.is_active ? "border-t" : "border-t text-muted-foreground line-through"}>
                  <td className="py-1.5">{r.service}<span className="block text-xs text-muted-foreground">{CATEGORY_LABELS[r.category]}{r.notes ? ` · ${r.notes}` : ""}</span></td>
                  <td className="text-xs">{BASIS_LABELS[r.basis]}</td>
                  <td className="text-xs">{season(r)}</td>
                  <td className="text-right tabular-nums">{money(r.unit_cost, r.currency)}</td>
                  <td className="text-right whitespace-nowrap">
                    <Button size="icon-xs" variant="ghost" aria-label={`Edit ${r.service}`} onClick={() => setEditing(r)}><Pencil aria-hidden /></Button>
                    <Button size="icon-xs" variant="ghost" aria-label={`Remove ${r.service}`} onClick={() => del.mutate(r.id)}><Trash2 aria-hidden /></Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
      {editing && (
        <RateDialog supplierId={supplierId} rate={editing === "new" ? null : editing} defaultCategory={TYPE_TO_CATEGORY[supplierType] ?? "other"} onClose={() => setEditing(null)} />
      )}
    </Card>
  );
}

function defaultBasis(c: PricingCategory): PricingBasis {
  return c === "hotel" ? "per_room" : c === "transport" ? "per_day" : "per_person";
}

function RateDialog({ supplierId, rate, defaultCategory, onClose }: { supplierId: number; rate: SupplierRate | null; defaultCategory: PricingCategory; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState<SupplierRateInput>({
    service: rate?.service ?? "", category: rate?.category ?? defaultCategory, basis: rate?.basis ?? defaultBasis(defaultCategory),
    unit_cost: rate ? String(Number(rate.unit_cost)) : "", currency: rate?.currency ?? "EUR", valid_from: rate?.valid_from ?? null, valid_to: rate?.valid_to ?? null,
    notes: rate?.notes ?? null, is_active: rate?.is_active ?? true,
  });
  const [error, setError] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: () => (rate ? pricingApi.updateRate(rate.id, f) : pricingApi.addRate(supplierId, f)),
    onSuccess: () => { toast.success(rate ? "Rate updated" : "Rate added"); void qc.invalidateQueries({ queryKey: ["supplier-rates"] }); onClose(); },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not save"),
  });
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={rate ? "Edit rate" : "Add rate"} formId="rate-form" submitLabel="Save" pending={save.isPending}>
      <form id="rate-form" className="space-y-4" onSubmit={(e) => {
        e.preventDefault();
        if (!f.service.trim() || f.unit_cost === "") { setError("Enter the service and the price."); return; }
        save.mutate();
      }}>
        <FormField label="Service" htmlFor="rt-service" required error={error ?? undefined}>
          <input id="rt-service" className={controlClass} maxLength={200} value={f.service} onChange={(e) => setF({ ...f, service: e.target.value })} placeholder="e.g. 49-seat coach with driver, per day" />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Category" htmlFor="rt-cat">
            <NativeSelect id="rt-cat" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value as PricingCategory })}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
            </NativeSelect>
          </FormField>
          <FormField label="Basis" htmlFor="rt-basis">
            <NativeSelect id="rt-basis" value={f.basis} onChange={(e) => setF({ ...f, basis: e.target.value as PricingBasis })}>
              {(Object.keys(BASIS_LABELS) as PricingBasis[]).map((b) => <option key={b} value={b}>{BASIS_LABELS[b]}</option>)}
            </NativeSelect>
          </FormField>
          <FormField label="Price" htmlFor="rt-cost" required>
            <input id="rt-cost" type="number" min={0} step="0.01" className={controlClass} value={f.unit_cost} onChange={(e) => setF({ ...f, unit_cost: e.target.value })} />
          </FormField>
          <FormField label="Currency" htmlFor="rt-cur">
            <NativeSelect id="rt-cur" value={f.currency} onChange={(e) => setF({ ...f, currency: e.target.value })}>{CURRENCIES.map((c) => <option key={c}>{c}</option>)}</NativeSelect>
          </FormField>
          <FormField label="Valid from" htmlFor="rt-from" hint="Leave empty for all year.">
            <input id="rt-from" type="date" className={controlClass} value={f.valid_from ?? ""} onChange={(e) => setF({ ...f, valid_from: e.target.value || null })} />
          </FormField>
          <FormField label="Valid to" htmlFor="rt-to">
            <input id="rt-to" type="date" className={controlClass} value={f.valid_to ?? ""} onChange={(e) => setF({ ...f, valid_to: e.target.value || null })} />
          </FormField>
        </div>
        <FormField label="Notes" htmlFor="rt-notes">
          <input id="rt-notes" className={controlClass} maxLength={500} value={f.notes ?? ""} onChange={(e) => setF({ ...f, notes: e.target.value || null })} placeholder="e.g. incl. driver up to 10 h/day, excl. tolls" />
        </FormField>
      </form>
    </FormDialog>
  );
}
