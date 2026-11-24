"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { NativeSelect, controlClass } from "@/components/common/form-controls";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, TableSkeleton } from "@/components/common/states";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { itinerariesApi } from "@/services/itineraries";
import { pricingApi } from "@/services/pricing";
import { CATEGORIES, CATEGORY_LABELS, type PricingUpdate, type PricingView } from "@/types/pricing";
import { CostLinesCard, NumberCell, StayRatesCard, money } from "./pricing-parts";

export const pricingKey = (id: number, version?: number) => ["pricing", id, version ?? "latest"] as const;
const CURRENCIES = ["INR", "USD", "GBP", "AED", "CHF", "SGD"];

export function PricingSheet({ id, version }: { id: number; version?: number }) {
  const qc = useQueryClient();
  const it = useQuery({ queryKey: ["itineraries", "detail", id, version ?? "latest"], queryFn: () => itinerariesApi.get(id, version) });
  const sheet = useQuery({ queryKey: pricingKey(id, version), queryFn: () => pricingApi.get(id, version) });
  const mutation = useMutation({
    mutationFn: ({ fn }: { fn: () => Promise<PricingView>; success?: string }) => fn(),
    onSuccess: (data, { success }) => {
      qc.setQueryData(pricingKey(id, version), data);
      void qc.invalidateQueries({ queryKey: ["proposal", id] });
      if (success) toast.success(success);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save"),
  });
  const run = (fn: () => Promise<PricingView>, success?: string) => mutation.mutate({ fn, success });
  const update = (body: PricingUpdate, success?: string) => run(() => pricingApi.update(id, body, version), success);

  const failed = it.error ?? sheet.error;
  if (failed) return <ErrorState message={failed instanceof ApiError ? failed.message : "Could not load the pricing."} onRetry={() => { void it.refetch(); void sheet.refetch(); }} />;
  if (!it.data || !sheet.data) return <TableSkeleton rows={8} />;
  const p = sheet.data;
  const cur = p.currency;
  const pct = p.margin_on_revenue_pct === null ? null : Number(p.margin_on_revenue_pct);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Pricing & costing"
        description={`${it.data.title} · ${it.data.customer_name ?? ""} · version ${p.version_number} (${p.version_label})`}
        actions={
          <>
            <span className={cn("mr-1 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-opacity", mutation.isPending ? "opacity-100" : "opacity-0")} role="status" aria-live="polite">
              <Loader2 className="size-3.5 animate-spin" aria-hidden /> Saving…
            </span>
            <Link href={`/itineraries/${id}${version ? `?version=${version}` : ""}`} className={buttonVariants({ variant: "outline" })}><ArrowLeft aria-hidden /> Itinerary</Link>
            <Link href={`/itineraries/${id}/proposal${version ? `?version=${version}` : ""}`} className={buttonVariants({ variant: "outline" })}><FileText aria-hidden /> PDF proposal</Link>
          </>
        }
      />
      <p className="rounded-lg border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        Internal page: costs, margins and profit are visible to YANA staff only. Customer PDFs show the selling prices only.
        {!p.margins_reviewed && " The default margins have not been reviewed by an administrator yet."}
      </p>
      {p.warnings.length > 0 && (
        <ul className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" aria-label="Pricing warnings">
          {p.warnings.map((w, i) => <li key={i} className="flex gap-2"><AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />{w}</li>)}
        </ul>
      )}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Selling prices</CardTitle></CardHeader>
            <CardContent>
              <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Selling prices">
                <PriceTile label="Per adult, twin sharing" value={p.prices.adult_twin} display={p.display_prices?.adult_twin} p={p} main />
                <PriceTile label="Single supplement" value={p.prices.single_supplement} display={p.display_prices?.single_supplement} p={p} />
                <PriceTile label="Child with bed" value={p.prices.child_with_bed} display={p.display_prices?.child_with_bed} p={p} />
                <PriceTile label="Child without bed" value={p.prices.child_without_bed} display={p.display_prices?.child_without_bed} p={p} />
              </dl>
              <dl className="mt-4 grid gap-3 border-t pt-4 text-sm sm:grid-cols-2 lg:grid-cols-5" aria-label="Internal figures">
                <Figure label="Cost per adult (twin)" value={money(p.adult_twin_cost, cur)} />
                <Figure label="Revenue (group)" value={money(p.revenue, cur, 0)} />
                <Figure label="Cost (group)" value={money(p.total_cost, cur, 0)} />
                <Figure label="Profit" value={money(p.profit, cur, 0)} tone={Number(p.profit) < 0 ? "bad" : "good"} />
                <Figure label="Margin on revenue" value={pct === null ? "—" : `${pct.toFixed(1)}%`} tone={pct !== null && pct < 0 ? "bad" : undefined} />
              </dl>
              {p.budget_per_person && (
                <p className={cn("mt-3 text-xs", Number(p.prices.adult_twin) > Number(p.budget_per_person) ? "text-amber-800" : "text-muted-foreground")}>
                  Customer budget: {money(p.budget_per_person, cur, 0)} per person{Number(p.prices.adult_twin) > Number(p.budget_per_person) ? " (the adult price is above it)" : ""}.
                </p>
              )}
            </CardContent>
          </Card>
          <CostLinesCard p={p} id={id} version={version} run={run} />
          <StayRatesCard p={p} id={id} version={version} run={run} />
        </div>

        <aside className="space-y-4" aria-label="Pricing settings">
          <Card>
            <CardHeader><CardTitle className="text-base">Margins</CardTitle><p className="text-xs text-muted-foreground">Added on top of cost, per category.</p></CardHeader>
            <CardContent className="space-y-2">
              {CATEGORIES.map((c) => {
                const cat = p.categories.find((x) => x.category === c);
                return (
                  <div key={c} className="grid grid-cols-[1fr_5.5rem] items-center gap-2 text-sm">
                    <div>
                      <span>{CATEGORY_LABELS[c]}</span>
                      {cat && <span className="block text-xs text-muted-foreground">{money(cat.per_person_cost, cur)} → {money(cat.per_person_selling, cur)} pp</span>}
                    </div>
                    <div className="relative">
                      <NumberCell label={`Margin for ${CATEGORY_LABELS[c]} (%)`} value={p.margins[c]} className="pr-6" step="0.5"
                        onCommit={(v) => v !== null && update({ margins: { [c]: v } }, "Margin updated")} />
                      <span className="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 text-xs text-muted-foreground">%</span>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Adjustments</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Discount (%)"><NumberCell label="Discount (%)" value={p.discount_pct} step="0.5" onCommit={(v) => v !== null && update({ discount_pct: v })} /></Row>
              <Row label="Adjustment per person" hint="Added to adult and child prices; can be negative.">
                <input type="number" step="1" aria-label="Adjustment per person" defaultValue={Number(p.adjustment_per_person)} key={p.adjustment_per_person}
                  className={cn(controlClass, "h-8 px-2 text-right")} onBlur={(e) => { const v = e.target.value; if (v !== "" && Number(v) !== Number(p.adjustment_per_person)) update({ adjustment_per_person: v }); }} />
              </Row>
              <Row label="Round prices up to">
                <NativeSelect aria-label="Round prices up to" className="h-8 text-xs" value={String(Number(p.rounding))}
                  onChange={(e) => { const rounding = e.target.value; update({ rounding }); }}>
                  <option value="0">No rounding (cents)</option>
                  {["1", "5", "10", "50", "100"].map((r) => <option key={r} value={r}>nearest {r}</option>)}
                </NativeSelect>
              </Row>
              <Row label="Child with bed: hotel share (%)" hint="Of the adult twin hotel share.">
                <NumberCell label="Child with bed hotel share (%)" value={p.child_bed_pct} step="5" onCommit={(v) => v !== null && update({ child_bed_pct: v })} />
              </Row>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Travellers</CardTitle>
              <p className="text-xs text-muted-foreground">From the enquiry: {p.travellers_from_enquiry.adults} adults, {p.travellers_from_enquiry.children} children, {p.travellers_from_enquiry.singles} single rooms.</p>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {([["adults", "Adults"], ["children_with_bed", "Children with bed"], ["children_without_bed", "Children without bed"], ["singles", "Adults in single rooms"]] as const).map(([k, label]) => (
                <Row key={k} label={label}>
                  <NumberCell label={label} value={String(p[k])} step="1" onCommit={(v) => v !== null && update({ [k]: Math.round(Number(v)) } as PricingUpdate)} />
                </Row>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Currency</CardTitle><p className="text-xs text-muted-foreground">Costs are in {cur}. Optionally show prices in another currency at a rate you enter (no live rates).</p></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Also show in">
                <NativeSelect aria-label="Display currency" className="h-8 text-xs" value={p.display_currency ?? ""}
                  onChange={(e) => { const c = e.target.value || null; update({ display_currency: c }); }}>
                  <option value="">— none —</option>
                  {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
                </NativeSelect>
              </Row>
              {p.display_currency && (
                <>
                  <Row label={`1 ${cur} =`} hint={p.display_currency}>
                    <NumberCell label="Exchange rate" value={p.exchange_rate} step="0.0001" placeholder="rate" onCommit={(v) => v !== null && update({ exchange_rate: v }, "Exchange rate updated")} />
                  </Row>
                  <Row label="PDF shows">
                    <NativeSelect aria-label="Currency in the PDF" className="h-8 text-xs" value={p.pdf_currency}
                      onChange={(e) => { const v = e.target.value as PricingView["pdf_currency"]; update({ pdf_currency: v }); }}>
                      <option value="base">{cur} only</option>
                      <option value="display">{p.display_currency} only</option>
                      <option value="both">Both</option>
                    </NativeSelect>
                  </Row>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Internal notes</CardTitle></CardHeader>
            <CardContent>
              <Textarea aria-label="Internal pricing notes" rows={3} defaultValue={p.notes ?? ""} key={p.notes ?? ""} placeholder="e.g. Coach quote from supplier pending"
                onBlur={(e) => { const v = e.target.value.trim() || null; if (v !== p.notes) update({ notes: v }, "Notes saved"); }} />
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function PriceTile({ label, value, display, p, main }: { label: string; value: string | null; display?: string | null; p: PricingView; main?: boolean }) {
  return (
    <div className={cn("rounded-lg border p-3", main && "border-brand-teal bg-accent/40")}>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("font-heading font-semibold tabular-nums", main ? "text-2xl" : "text-lg")}>{value === null ? "—" : money(value, p.currency, Number(value) % 1 ? 2 : 0)}</dd>
      {display && p.display_prices && <dd className="text-xs text-muted-foreground tabular-nums">{money(display, p.display_prices.currency, 0)}</dd>}
    </div>
  );
}

function Figure({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("font-medium tabular-nums", tone === "bad" && "text-destructive", tone === "good" && "text-emerald-700")}>{value}</dd>
    </div>
  );
}

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[1fr_7rem] items-center gap-2">
      <div><span>{label}</span>{hint && <span className="block text-xs text-muted-foreground">{hint}</span>}</div>
      {children}
    </div>
  );
}
