"use client";

import { useState } from "react";
import { Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";
import { FormField, NativeSelect, controlClass } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { pricingApi } from "@/services/pricing";
import { BASIS_LABELS, CATEGORIES, CATEGORY_LABELS, type ManualLine, type PricingBasis, type PricingCategory, type PricingLine, type PricingView } from "@/types/pricing";

export type Run = (fn: () => Promise<PricingView>, success?: string) => void;

export function money(amount: string | number | null | undefined, currency: string, decimals = 2): string {
  if (amount === null || amount === undefined || amount === "") return "—";
  try {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency, minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(Number(amount));
  } catch {
    return `${amount} ${currency}`;
  }
}

/** Number input that saves when the field is left or Enter is pressed (not on every keystroke). */
export function NumberCell({ value, onCommit, label, placeholder, className, allowEmpty = false, step = "0.01" }: {
  value: string | null; onCommit: (v: string | null) => void; label: string; placeholder?: string; className?: string; allowEmpty?: boolean; step?: string;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const shown = draft ?? (value === null ? "" : String(Number(value)));
  const commit = () => {
    if (draft === null) return;
    const v = draft.trim();
    setDraft(null);
    if (v === "" && !allowEmpty) return;
    if (v !== "" && (Number.isNaN(Number(v)) || Number(v) < 0)) return;
    const next = v === "" ? null : v;
    if (next === null ? value !== null : value === null || Number(next) !== Number(value)) onCommit(next);
  };
  return (
    <input type="number" inputMode="decimal" min={0} step={step} aria-label={label} placeholder={placeholder} value={shown}
      onChange={(e) => setDraft(e.target.value)} onBlur={commit} onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
      className={cn(controlClass, "h-8 px-2 text-right tabular-nums", className)} />
  );
}

export function CostLinesCard({ p, id, version, run }: { p: PricingView; id: number; version?: number; run: Run }) {
  const [editing, setEditing] = useState<PricingLine | "new" | null>(null);
  const groups = CATEGORIES.map((c) => ({ c, lines: p.lines.filter((l) => l.category === c) })).filter((g) => g.lines.length);
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <div>
          <CardTitle className="text-base">Cost lines</CardTitle>
          <p className="text-xs text-muted-foreground">From the itinerary and inventory (estimates unless verified). Change a cost or quantity to override it for this proposal.</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setEditing("new")}><Plus aria-hidden /> Add cost line</Button>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="text-left text-xs text-muted-foreground">
            <tr><th className="py-1.5 pr-2 font-medium">Include</th><th className="pr-2 font-medium">Item</th><th className="pr-2 font-medium">Basis</th>
              <th className="w-28 pr-2 text-right font-medium">Unit cost</th><th className="w-24 pr-2 text-right font-medium">Qty</th><th className="w-28 pr-2 text-right font-medium">Total</th><th className="w-16" /></tr>
          </thead>
          {groups.map(({ c, lines }) => (
            <tbody key={c} className="border-t">
              <tr><td colSpan={7} className="pt-3 pb-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">{CATEGORY_LABELS[c]}</td></tr>
              {lines.map((l) => (
                <tr key={l.key} className={cn("align-middle", !l.included && "text-muted-foreground line-through")}>
                  <td className="py-1 pr-2">
                    {l.manual_id ? null : (
                      <input type="checkbox" checked={l.included} aria-label={`Include ${l.description}`} className="size-4"
                        onChange={(e) => { const included = e.target.checked; run(() => pricingApi.override(id, { key: l.key, included }, version)); }} />
                    )}
                  </td>
                  <td className="py-1 pr-2">
                    <span>{l.description}</span>{" "}
                    {l.unit_cost === null && <Badge variant="outline" className="border-amber-300 text-amber-800">No price</Badge>}
                    {l.unit_cost !== null && l.is_estimate && <Badge variant="outline" className="text-muted-foreground">Estimate</Badge>}
                    {l.is_overridden && <Badge variant="outline" className="border-sky-300 text-sky-800" title={l.auto_unit_cost ? `Inventory: ${money(l.auto_unit_cost, p.currency)}` : "No inventory price"}>Edited</Badge>}
                    {l.manual_id && <Badge variant="outline">Added</Badge>}
                  </td>
                  <td className="py-1 pr-2 text-xs text-muted-foreground">{BASIS_LABELS[l.basis]}</td>
                  <td className="py-1 pr-2">
                    {l.manual_id ? <span className="block text-right tabular-nums">{money(l.unit_cost, p.currency)}</span> : (
                      <NumberCell label={`Unit cost of ${l.description}`} value={l.unit_cost} placeholder="price" allowEmpty
                        onCommit={(v) => run(() => pricingApi.override(id, v === null ? { key: l.key, clear_unit_cost: true } : { key: l.key, unit_cost: v }, version), "Cost updated")} />
                    )}
                  </td>
                  <td className="py-1 pr-2">
                    {l.manual_id ? <span className="block text-right tabular-nums">{Number(l.quantity)}</span> : (
                      <NumberCell label={`Quantity of ${l.description}`} value={l.quantity} step="1"
                        onCommit={(v) => v !== null && run(() => pricingApi.override(id, { key: l.key, quantity: v }, version), "Quantity updated")} />
                    )}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums">{money(l.total, p.currency)}</td>
                  <td className="py-1 text-right whitespace-nowrap">
                    {l.manual_id ? (
                      <>
                        <Button size="icon-xs" variant="ghost" aria-label={`Edit ${l.description}`} onClick={() => setEditing(l)}><Pencil aria-hidden /></Button>
                        <Button size="icon-xs" variant="ghost" aria-label={`Remove ${l.description}`} onClick={() => run(() => pricingApi.deleteLine(id, l.manual_id!, version), "Cost line removed")}><Trash2 aria-hidden /></Button>
                      </>
                    ) : l.is_overridden ? (
                      <Button size="icon-xs" variant="ghost" aria-label={`Back to inventory values for ${l.description}`} title="Back to inventory values"
                        onClick={() => run(() => pricingApi.resetOverride(id, l.key, version), "Back to inventory values")}><RotateCcw aria-hidden /></Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
          <tfoot className="border-t-2 font-semibold">
            <tr><td colSpan={5} className="py-2 pr-2 text-right">Total cost for the group</td><td className="py-2 pr-2 text-right tabular-nums">{money(p.total_cost, p.currency)}</td><td /></tr>
          </tfoot>
        </table>
      </CardContent>
      {editing && <LineDialog line={editing === "new" ? null : editing} onClose={() => setEditing(null)}
        onSave={(body) => run(() => editing === "new" ? pricingApi.addLine(id, body, version) : pricingApi.updateLine(id, editing.manual_id!, body, version), editing === "new" ? "Cost line added" : "Cost line updated")} />}
    </Card>
  );
}

function LineDialog({ line, onClose, onSave }: { line: PricingLine | null; onClose: () => void; onSave: (body: ManualLine) => void }) {
  const [f, setF] = useState<ManualLine>({
    category: line?.category ?? "guide", basis: line?.basis ?? "per_day", description: line?.description ?? "",
    unit_cost: line?.unit_cost ?? "", quantity: line ? String(Number(line.quantity)) : "1", is_estimate: line?.is_estimate ?? true,
  });
  const [error, setError] = useState<string | null>(null);
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={line ? "Edit cost line" : "Add cost line"}
      description="For costs not in the itinerary: guides, tolls, parking, porterage, extras." formId="cost-line-form" submitLabel={line ? "Save" : "Add"}>
      <form id="cost-line-form" className="space-y-4" onSubmit={(e) => {
        e.preventDefault();
        if (!f.description.trim()) { setError("Enter a description."); return; }
        onSave({ ...f, description: f.description.trim(), unit_cost: f.unit_cost === "" ? null : f.unit_cost });
        onClose();
      }}>
        <FormField label="Description" htmlFor="cl-desc" required error={error ?? undefined}>
          <input id="cl-desc" className={controlClass} maxLength={300} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="e.g. Licensed guide in Paris" />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Category" htmlFor="cl-cat">
            <NativeSelect id="cl-cat" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value as PricingCategory })}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
            </NativeSelect>
          </FormField>
          <FormField label="Basis" htmlFor="cl-basis" hint="Per person: once per traveller. Others are shared by the group.">
            <NativeSelect id="cl-basis" value={f.basis} onChange={(e) => setF({ ...f, basis: e.target.value as PricingBasis })}>
              {(Object.keys(BASIS_LABELS) as PricingBasis[]).filter((b) => b !== "per_room").map((b) => <option key={b} value={b}>{BASIS_LABELS[b]}</option>)}
            </NativeSelect>
          </FormField>
          <FormField label="Unit cost" htmlFor="cl-unit" hint="Leave empty if not known yet.">
            <input id="cl-unit" type="number" min={0} step="0.01" className={controlClass} value={f.unit_cost ?? ""} onChange={(e) => setF({ ...f, unit_cost: e.target.value })} />
          </FormField>
          <FormField label="Quantity" htmlFor="cl-qty" hint="e.g. number of days">
            <input id="cl-qty" type="number" min={0} step="1" className={controlClass} value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value || "0" })} />
          </FormField>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="size-4" checked={!f.is_estimate} onChange={(e) => setF({ ...f, is_estimate: !e.target.checked })} /> Confirmed by the supplier (not an estimate)</label>
      </form>
    </FormDialog>
  );
}

export function StayRatesCard({ p, id, version, run }: { p: PricingView; id: number; version?: number; run: Run }) {
  if (!p.stays.length) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Room rates used for per-person prices</CardTitle>
        <p className="text-xs text-muted-foreground">Per room per night. The adult twin price uses half the double rate; the single supplement uses the single rate minus that half.</p>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead className="text-left text-xs text-muted-foreground"><tr><th className="py-1.5 pr-2 font-medium">Hotel</th><th className="pr-2 font-medium">Nights</th><th className="w-32 pr-2 text-right font-medium">Double</th><th className="w-32 pr-2 text-right font-medium">Single</th><th className="w-10" /></tr></thead>
          <tbody>
            {p.stays.map((s) => (
              <tr key={s.key} className="border-t">
                <td className="py-1.5 pr-2">{s.label} {s.single_is_estimate && <Badge variant="outline" className="border-amber-300 text-amber-800" title="No single room type in inventory: the double rate is used for single use">Single = double</Badge>}</td>
                <td className="pr-2">{s.nights}</td>
                <td className="pr-2"><NumberCell label={`Double rate at ${s.label}`} value={s.double_rate} placeholder="rate"
                  onCommit={(v) => run(() => pricingApi.stayRate(id, { key: s.key, double_rate: v, single_rate: s.is_overridden ? s.single_rate : null }, version), "Room rate updated")} /></td>
                <td className="pr-2"><NumberCell label={`Single rate at ${s.label}`} value={s.single_rate} placeholder="= double" allowEmpty
                  onCommit={(v) => run(() => pricingApi.stayRate(id, { key: s.key, double_rate: s.is_overridden ? s.double_rate : null, single_rate: v }, version), "Room rate updated")} /></td>
                <td className="text-right">
                  {s.is_overridden && <Button size="icon-xs" variant="ghost" aria-label={`Back to inventory rates for ${s.label}`} title="Back to inventory rates"
                    onClick={() => run(() => pricingApi.stayRate(id, { key: s.key }, version), "Back to inventory rates")}><RotateCcw aria-hidden /></Button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
