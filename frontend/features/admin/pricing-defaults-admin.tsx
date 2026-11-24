"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Save } from "lucide-react";
import { toast } from "sonner";
import { Toggle } from "@/components/common/choice-controls";
import { FormField, NativeSelect, controlClass } from "@/components/common/form-controls";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/services/api";
import { pricingApi } from "@/services/pricing";
import { CATEGORIES, CATEGORY_LABELS, type PricingDefaults } from "@/types/pricing";

export function PricingDefaultsAdmin() {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["settings", "pricing"], queryFn: pricingApi.defaults });
  const [draft, setDraft] = useState<PricingDefaults | null>(null);
  if (draft === null && query.data) setDraft(query.data);
  const set = (patch: Partial<PricingDefaults>) => setDraft((d) => (d ? { ...d, ...patch } : d));
  const save = useMutation({
    mutationFn: () => pricingApi.saveDefaults(draft!),
    onSuccess: (d) => { setDraft(d); qc.setQueryData(["settings", "pricing"], d); toast.success("Pricing defaults saved"); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save"),
  });

  if (query.error) return <ErrorState message={query.error instanceof ApiError ? query.error.message : "Could not load the pricing defaults."} onRetry={() => void query.refetch()} />;
  if (!draft) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const dirty = JSON.stringify(draft) !== JSON.stringify(query.data);

  return (
    <div className="space-y-6">
      <PageHeader title="Pricing defaults" description="Copied into each new pricing sheet. Planners can change them per proposal; existing sheets are not changed."
        actions={<Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}><Save aria-hidden /> Save</Button>} />
      {!draft.margins_reviewed && (
        <p className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
          The margins below are placeholders (15% for every category). Set YANA&apos;s margins, then switch on “Margins reviewed”.
        </p>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Margin per category</CardTitle><p className="text-xs text-muted-foreground">Percentage added on top of cost.</p></CardHeader>
          <CardContent className="space-y-3">
            {CATEGORIES.map((c) => (
              <div key={c} className="grid grid-cols-[1fr_7rem] items-center gap-3">
                <label htmlFor={`pd-m-${c}`} className="text-sm">{CATEGORY_LABELS[c]}</label>
                <div className="relative">
                  <input id={`pd-m-${c}`} type="number" min={0} max={300} step="0.5" className={`${controlClass} pr-7 text-right`}
                    value={draft.margins[c] === undefined ? "" : String(Number(draft.margins[c]))}
                    onChange={(e) => set({ margins: { ...draft.margins, [c]: e.target.value || "0" } })} />
                  <span className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-xs text-muted-foreground">%</span>
                </div>
              </div>
            ))}
            <Toggle id="pd-reviewed" checked={draft.margins_reviewed} onChange={(v) => set({ margins_reviewed: v })} label="Margins reviewed" hint="Confirms these are YANA's agreed margins." />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Prices</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <FormField label="Round prices up to" htmlFor="pd-round">
              <NativeSelect id="pd-round" value={String(Number(draft.rounding))} onChange={(e) => set({ rounding: e.target.value })}>
                <option value="0">No rounding (cents)</option>
                {["1", "5", "10", "50", "100"].map((r) => <option key={r} value={r}>nearest {r}</option>)}
              </NativeSelect>
            </FormField>
            <FormField label="Child with bed: hotel share (%)" htmlFor="pd-child" hint="Share of the adult twin hotel cost charged for a child with a bed.">
              <input id="pd-child" type="number" min={0} max={100} step="5" className={controlClass} value={String(Number(draft.child_bed_pct))} onChange={(e) => set({ child_bed_pct: e.target.value || "0" })} />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Also show prices in" htmlFor="pd-cur">
                <NativeSelect id="pd-cur" value={draft.display_currency ?? ""} onChange={(e) => set({ display_currency: e.target.value || null })}>
                  <option value="">— none —</option>
                  {["INR", "USD", "GBP", "AED", "CHF", "SGD"].map((c) => <option key={c}>{c}</option>)}
                </NativeSelect>
              </FormField>
              <FormField label="Exchange rate (1 EUR =)" htmlFor="pd-rate" hint="Typed in; no live rates.">
                <input id="pd-rate" type="number" min={0} step="0.0001" className={controlClass} disabled={!draft.display_currency}
                  value={draft.exchange_rate ?? ""} onChange={(e) => set({ exchange_rate: e.target.value || null })} />
              </FormField>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
