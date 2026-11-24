"use client";

import { ArrowDown, ArrowUp, ImageOff, Sparkles } from "lucide-react";
import { Segmented, Toggle } from "@/components/common/choice-controls";
import { FormField, NativeSelect, controlClass } from "@/components/common/form-controls";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ProposalOptions, ProposalSettings } from "@/types/proposal";

type Change = (patch: Partial<ProposalSettings>) => void;

export function Panel({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3 border-b pb-5 last:border-b-0">
      <div>
        <h2 className="text-sm font-semibold">{title}</h2>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  );
}

export function TemplatePanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  return (
    <Panel title="Template">
      <div role="radiogroup" aria-label="Template" className="grid gap-2">
        {options.templates.map((t) => (
          <button key={t.key} type="button" role="radio" aria-checked={s.template === t.key} onClick={() => onChange({ template: t.key })}
            className={cn("rounded-lg border p-2.5 text-left transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
              s.template === t.key ? "border-brand-teal bg-accent" : "hover:bg-muted/60")}>
            <span className="block text-sm font-medium">{t.label}</span>
            <span className="block text-xs text-muted-foreground">{t.description}</span>
          </button>
        ))}
      </div>
      <div className="space-y-1.5">
        <p className="text-sm font-medium">Branding</p>
        <Segmented label="Branding" size="sm" value={s.branding} onChange={(v) => onChange({ branding: v as ProposalSettings["branding"] })}
          options={[{ value: "agent", label: "Travel agent" }, { value: "yana", label: "YANA" }, { value: "both", label: "Both" }]} />
        <p className="text-xs text-muted-foreground">
          {s.branding === "agent" ? "White label: “Curated by” the agent, with the agent's contact details." : s.branding === "yana" ? "YANA name, logo and contact details." : "Agent first, “in partnership with” YANA, with both contacts."}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <ColourField id="pd-primary" label="Heading colour" value={s.primary_color} onChange={(v) => onChange({ primary_color: v })} />
        <ColourField id="pd-accent" label="Accent colour" value={s.accent_color} onChange={(v) => onChange({ accent_color: v })} />
      </div>
    </Panel>
  );
}

function ColourField({ id, label, value, onChange }: { id: string; label: string; value: string | null; onChange: (v: string | null) => void }) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="text-xs font-medium">{label}</label>
      <div className="flex items-center gap-2">
        <input id={id} type="color" value={value ?? "#1f3b64"} onChange={(e) => onChange(e.target.value)}
          className={cn("h-8 w-10 cursor-pointer rounded border p-0.5", !value && "opacity-40")} aria-describedby={`${id}-hint`} />
        {value ? <button type="button" className="text-xs text-muted-foreground underline" onClick={() => onChange(null)}>Template default</button>
          : <span id={`${id}-hint`} className="text-xs text-muted-foreground">Template default</span>}
      </div>
    </div>
  );
}

/** Text that is automatic until the planner chooses to edit it (null = automatic). */
function AutoText({ id, label, value, auto, onChange, rows = 3, input }: {
  id: string; label: string; value: string | null; auto: string; onChange: (v: string | null) => void; rows?: number; input?: boolean;
}) {
  const custom = value !== null;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium">{label}</label>
        {custom ? (
          <button type="button" className="inline-flex items-center gap-1 text-xs text-brand-teal hover:underline" onClick={() => onChange(null)}>
            <Sparkles className="size-3" aria-hidden /> Use automatic text
          </button>
        ) : <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Sparkles className="size-3" aria-hidden /> Automatic</span>}
      </div>
      {input ? (
        <input id={id} className={controlClass} value={value ?? auto} onChange={(e) => onChange(e.target.value)} maxLength={120} />
      ) : (
        <Textarea id={id} rows={rows} value={value ?? auto} onChange={(e) => onChange(e.target.value)} className={cn(!custom && "text-muted-foreground")} />
      )}
    </div>
  );
}

export function TextPanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  const d = options.defaults;
  return (
    <Panel title="Text" description="Automatic texts come from the itinerary and the YANA defaults. Edit any of them for this proposal.">
      <AutoText id="pd-title" label="Title" input value={s.title} auto={d.title} onChange={(v) => onChange({ title: v })} />
      <AutoText id="pd-intro" label="Introduction" rows={4} value={s.intro} auto={d.intro} onChange={(v) => onChange({ intro: v })} />
      <AutoText id="pd-closing" label="Closing message" rows={2} value={s.closing} auto={d.closing} onChange={(v) => onChange({ closing: v })} />
      <Toggle id="pd-hotel-names" checked={s.hotel_names_in_days} onChange={(v) => onChange({ hotel_names_in_days: v })}
        label="Hotel names in the day-by-day text" hint="Off: “Check in to your hotel in Paris.”" />
    </Panel>
  );
}

export function SectionsPanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  const label = (k: string) => options.sections.find((x) => x.key === k)?.label ?? k;
  const move = (i: number, by: number) => {
    const next = [...s.sections];
    const [item] = next.splice(i, 1);
    next.splice(i + by, 0, item);
    onChange({ sections: next });
  };
  return (
    <Panel title="Sections" description="Switch sections on or off and change their order.">
      <ul className="space-y-1" aria-label="Sections">
        {s.sections.map((sec, i) => (
          <li key={sec.key} className="flex items-center gap-2 rounded-md border px-2 py-1.5">
            <input id={`pd-sec-${sec.key}`} type="checkbox" checked={sec.enabled} className="size-4 accent-[var(--color-brand-teal)]"
              onChange={(e) => { const enabled = e.target.checked; onChange({ sections: s.sections.map((x) => x.key === sec.key ? { ...x, enabled } : x) }); }} />
            <label htmlFor={`pd-sec-${sec.key}`} className={cn("flex-1 text-sm", !sec.enabled && "text-muted-foreground line-through")}>{label(sec.key)}</label>
            <Button type="button" size="icon-xs" variant="ghost" disabled={i === 0} onClick={() => move(i, -1)} aria-label={`Move ${label(sec.key)} up`}><ArrowUp aria-hidden /></Button>
            <Button type="button" size="icon-xs" variant="ghost" disabled={i === s.sections.length - 1} onClick={() => move(i, 1)} aria-label={`Move ${label(sec.key)} down`}><ArrowDown aria-hidden /></Button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function PricePanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  return (
    <Panel title="Price" description="The selling price shown to the customer. Without one, the PDF says “Price on request”.">
      <div className="grid grid-cols-[1fr_5.5rem] gap-2">
        <FormField label="Price per person" htmlFor="pd-price">
          <input id="pd-price" className={controlClass} inputMode="decimal" placeholder="e.g. 2950" value={s.price_per_person ?? ""}
            onChange={(e) => { const v = e.target.value.replace(/[^\d.]/g, ""); onChange({ price_per_person: v === "" ? null : v }); }} />
        </FormField>
        <FormField label="Currency" htmlFor="pd-currency">
          <NativeSelect id="pd-currency" value={s.price_currency} onChange={(e) => onChange({ price_currency: e.target.value })}>
            {["EUR", "INR", "USD", "GBP", "CHF", "AED"].map((c) => <option key={c}>{c}</option>)}
          </NativeSelect>
        </FormField>
      </div>
      <FormField label="Price note" htmlFor="pd-price-note">
        <input id="pd-price-note" className={controlClass} placeholder="e.g. Per person sharing a twin room, minimum 20 travellers" maxLength={300}
          value={s.price_note ?? ""} onChange={(e) => onChange({ price_note: e.target.value || null })} />
      </FormField>
      {options.internal_estimate_per_person && (
        <p className="rounded-md bg-amber-50 px-2.5 py-2 text-xs text-amber-900">
          Internal only (never in the PDF): estimated cost {formatMoney(options.internal_estimate_per_person, options.currency)} per person, from inventory prices.
        </p>
      )}
    </Panel>
  );
}

export function ListsPanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  const d = options.defaults;
  return (
    <Panel title="Inclusions, exclusions and terms" description="One item per line.">
      <AutoText id="pd-inclusions" label="Inclusions" rows={6} value={s.inclusions?.join("\n") ?? null} auto={d.inclusions.join("\n")}
        onChange={(v) => onChange({ inclusions: v === null ? null : v.split("\n") })} />
      <AutoText id="pd-exclusions" label="Exclusions" rows={5} value={s.exclusions?.join("\n") ?? null} auto={d.exclusions.join("\n")}
        onChange={(v) => onChange({ exclusions: v === null ? null : v.split("\n") })} />
      <AutoText id="pd-terms" label="Terms and conditions" rows={5} value={s.terms} auto={d.terms} onChange={(v) => onChange({ terms: v })} />
    </Panel>
  );
}

export function PhotosPanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  const set = (day: number, value: number | null) => {
    const next = { ...s.day_images };
    if (value === null) delete next[String(day)];
    else next[String(day)] = value;
    onChange({ day_images: next });
  };
  const anyPhotos = options.day_images.some((d) => d.choices.length);
  return (
    <Panel title="Day photos" description={anyPhotos ? "Automatic picks the first sightseeing photo, then the hotel, then the city." : "No photos yet. Add photos to sightseeing, hotels or cities in Destination Inventory and they appear here."}>
      {anyPhotos && (
        <ul className="space-y-3">
          {options.day_images.map((d) => {
            const current = s.day_images[String(d.day_number)];
            return (
              <li key={d.day_number}>
                <p className="mb-1 text-xs font-medium">Day {d.day_number} · {d.title}</p>
                <div role="radiogroup" aria-label={`Photo for day ${d.day_number}`} className="flex flex-wrap gap-1.5">
                  <PhotoChoice on={current === undefined} onClick={() => set(d.day_number, null)} label="Automatic"><Sparkles className="size-4" aria-hidden /></PhotoChoice>
                  <PhotoChoice on={current === 0} onClick={() => set(d.day_number, 0)} label="No photo"><ImageOff className="size-4" aria-hidden /></PhotoChoice>
                  {d.choices.map((c) => (
                    <PhotoChoice key={c.media_id} on={current === c.media_id} onClick={() => set(d.day_number, c.media_id)} label={c.label}>
                      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                      <img src={c.url} alt="" className="size-full object-cover" />
                    </PhotoChoice>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

function PhotoChoice({ on, onClick, label, children }: { on: boolean; onClick: () => void; label: string; children: React.ReactNode }) {
  return (
    <button type="button" role="radio" aria-checked={on} aria-label={label} title={label} onClick={onClick}
      className={cn("flex size-12 items-center justify-center overflow-hidden rounded-md border text-muted-foreground transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
        on ? "border-2 border-brand-teal bg-accent text-foreground" : "hover:bg-muted/60")}>
      {children}
    </button>
  );
}
