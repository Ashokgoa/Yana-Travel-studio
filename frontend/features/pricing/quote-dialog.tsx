"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleDashed, MessageSquareQuote } from "lucide-react";
import { Segmented } from "@/components/common/choice-controls";
import { FormField, NativeSelect, controlClass } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { inventoryApi } from "@/services/inventory";
import { pricingApi } from "@/services/pricing";
import { BASIS_LABELS, CATEGORY_LABELS, type PricingLine, type PricingView, type QuoteStatus, type SupplierRate } from "@/types/pricing";
import { money, type Run } from "./pricing-parts-shared";

const CURRENCIES = ["EUR", "CHF", "GBP", "USD", "SEK", "NOK", "DKK", "CZK", "HUF", "PLN", "INR"];

export const STATUS_STYLE: Record<QuoteStatus, { label: string; className: string }> = {
  estimate: { label: "Estimate", className: "border-border text-muted-foreground" },
  quoted: { label: "Quoted", className: "border-sky-300 bg-sky-50 text-sky-800" },
  confirmed: { label: "Confirmed", className: "border-emerald-300 bg-emerald-50 text-emerald-800" },
};

export function StatusBadge({ status }: { status: QuoteStatus }) {
  const s = STATUS_STYLE[status];
  return (
    <Badge variant="outline" className={s.className}>
      {status === "confirmed" ? <CheckCircle2 className="size-3" aria-hidden /> : status === "quoted" ? <MessageSquareQuote className="size-3" aria-hidden /> : <CircleDashed className="size-3" aria-hidden />}
      {s.label}
    </Badge>
  );
}

/** Record a supplier's price for one cost line: pick a supplier, its rates pop up, click one, edit if needed. */
export function QuoteDialog({ line, p, id, version, run, onClose }: { line: PricingLine; p: PricingView; id: number; version?: number; run: Run; onClose: () => void }) {
  const q = line.quote;
  const [supplierId, setSupplierId] = useState<number | null>(q?.supplier_id ?? line.supplier_id ?? null);
  const [rateId, setRateId] = useState<number | null>(q?.supplier_rate_id ?? null);
  const [amount, setAmount] = useState<string>(q?.amount ?? (line.unit_cost ? String(Number(line.unit_cost)) : ""));
  const [currency, setCurrency] = useState<string>(q?.currency ?? p.currency);
  const [fx, setFx] = useState<string>(q?.fx_rate ?? "");
  const [status, setStatus] = useState<QuoteStatus>(q?.status && q.status !== "estimate" ? q.status : "quoted");
  const [reference, setReference] = useState<string>(q?.reference ?? "");
  const [saveAsRate, setSaveAsRate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The API returns at most 100 per page; enough for a supplier picker (search can come later if needed).
  const suppliers = useQuery({ queryKey: ["inventory", "suppliers", "list", { active: true, page_size: 100 }], queryFn: () => inventoryApi.list("suppliers", { active: true, page_size: 100 }) });
  const rates = useQuery({
    queryKey: ["supplier-rates", line.category, p.trip_start, supplierId],
    queryFn: () => pricingApi.rates({ category: line.category, on: p.trip_start, supplier_id: supplierId ?? undefined }),
  });
  const foreign = currency !== p.currency;
  const rate = foreign ? Number(fx || p.fx_rates[currency] || 0) : 1;
  const unit = Number(amount) * rate;

  const pick = (r: SupplierRate) => {
    setRateId(r.id);
    setSupplierId(r.supplier_id);
    setAmount(String(Number(r.unit_cost)));
    setCurrency(r.currency);
    if (r.currency !== p.currency && !fx) setFx(p.fx_rates[r.currency] ?? "");
    setSaveAsRate(false);
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Supplier price" wide formId="quote-form" submitLabel="Save price"
      description={`${line.description} · ${CATEGORY_LABELS[line.category]}, ${BASIS_LABELS[line.basis]}. Trip starts ${formatDate(p.trip_start)}.`}>
      <form id="quote-form" className="space-y-4" onSubmit={(e) => {
        e.preventDefault();
        if (amount === "" || Number.isNaN(Number(amount)) || Number(amount) < 0) { setError("Enter the price."); return; }
        if (foreign && !(rate > 0)) { setError(`Enter the exchange rate: 1 ${currency} = ? ${p.currency}.`); return; }
        run(() => pricingApi.quote(id, {
          key: line.key, supplier_id: supplierId, supplier_rate_id: rateId, amount, currency, fx_rate: foreign ? String(rate) : null,
          status, reference: reference || null, save_as_rate: saveAsRate, service: line.description,
        }, version), "Supplier price saved");
        onClose();
      }}>
        <FormField label="Supplier" htmlFor="qd-supplier">
          <NativeSelect id="qd-supplier" value={supplierId ?? ""} onChange={(e) => { const v = e.target.value; setSupplierId(v ? Number(v) : null); setRateId(null); }}>
            <option value="">— any supplier —</option>
            {suppliers.data?.items.map((s) => <option key={s.id} value={s.id}>{String(s.name)} ({String(s.supplier_type)})</option>)}
          </NativeSelect>
        </FormField>

        <div className="space-y-1.5">
          <p className="text-sm font-medium">Rates on file{supplierId ? "" : ` for ${CATEGORY_LABELS[line.category].toLowerCase()}`}</p>
          {rates.isPending ? <p className="text-xs text-muted-foreground">Loading…</p> : !rates.data?.length ? (
            <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">No rates on file{supplierId ? " for this supplier" : ""}. Type the price you got below{supplierId ? " and tick “Save to the supplier's rate card” to reuse it" : ""}.</p>
          ) : (
            <ul role="radiogroup" aria-label="Rates" className="max-h-52 space-y-1.5 overflow-y-auto pr-1">
              {rates.data.map((r) => (
                <li key={r.id}>
                  <button type="button" role="radio" aria-checked={rateId === r.id} onClick={() => pick(r)}
                    className={cn("flex w-full items-center gap-2 rounded-md border px-2.5 py-1.5 text-left text-sm transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                      rateId === r.id ? "border-brand-teal bg-accent" : "hover:bg-muted/60")}>
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">{r.service}</span>
                      <span className="block text-xs text-muted-foreground">
                        {supplierId ? "" : `${r.supplier_name} · `}{BASIS_LABELS[r.basis]}
                        {r.valid_from || r.valid_to ? ` · ${r.valid_from ? formatDate(r.valid_from) : "…"} – ${r.valid_to ? formatDate(r.valid_to) : "…"}` : ""}
                        {r.basis !== line.basis ? ` · different basis (line is ${BASIS_LABELS[line.basis]})` : ""}
                      </span>
                    </span>
                    <span className="text-right tabular-nums">{money(r.unit_cost, r.currency)}</span>
                    {r.valid_on_trip === false && <Badge variant="outline" className="text-muted-foreground">Other season</Badge>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <FormField label="Price per unit" htmlFor="qd-amount" required error={error ?? undefined}>
            <input id="qd-amount" type="number" min={0} step="0.01" className={controlClass} value={amount}
              onChange={(e) => { setAmount(e.target.value); setRateId(null); setError(null); }} />
          </FormField>
          <FormField label="Currency" htmlFor="qd-currency">
            <NativeSelect id="qd-currency" value={currency} onChange={(e) => { const c = e.target.value; setCurrency(c); setRateId(null); if (c !== p.currency) setFx(p.fx_rates[c] ?? ""); }}>
              {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
            </NativeSelect>
          </FormField>
          {foreign && (
            <FormField label={`1 ${currency} = ? ${p.currency}`} htmlFor="qd-fx" hint="Your rate; saved for this quote.">
              <input id="qd-fx" type="number" min={0} step="0.0001" className={controlClass} value={fx} placeholder={p.fx_rates[currency] ?? "e.g. 1.06"} onChange={(e) => setFx(e.target.value)} />
            </FormField>
          )}
        </div>
        {amount !== "" && rate > 0 && (
          <p className="text-xs text-muted-foreground">
            = {money(unit, p.currency)} {BASIS_LABELS[line.basis]} · line total about {money(unit * Number(line.quantity) * (line.basis === "per_person" ? p.adults + p.children_with_bed + p.children_without_bed : 1), p.currency)}
          </p>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Status</p>
            <Segmented label="Status" size="sm" value={status} onChange={(v) => setStatus(v as QuoteStatus)}
              options={[{ value: "estimate", label: "Estimate" }, { value: "quoted", label: "Quoted" }, { value: "confirmed", label: "Confirmed" }]} />
          </div>
          <FormField label="Reference" htmlFor="qd-ref" hint="e.g. email 24 Nov, offer no. 123">
            <input id="qd-ref" className={controlClass} maxLength={200} value={reference} onChange={(e) => setReference(e.target.value)} />
          </FormField>
        </div>
        {supplierId && !rateId && (
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="size-4" checked={saveAsRate} onChange={(e) => setSaveAsRate(e.target.checked)} /> Save to the supplier&apos;s rate card for next time</label>
        )}
        {q && (
          <Button type="button" variant="ghost" size="sm" onClick={() => { run(() => pricingApi.clearQuote(id, line.key, version), "Supplier price removed"); onClose(); }}>
            Remove the supplier price (back to the inventory estimate)
          </Button>
        )}
      </form>
    </FormDialog>
  );
}
