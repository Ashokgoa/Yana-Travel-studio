"use client";

import { useRef, useState } from "react";
import { ChevronDown, ImageOff, ImagePlus, Images, Loader2, RotateCcw, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { controlClass } from "@/components/common/form-controls";
import { Textarea } from "@/components/ui/textarea";
import { MediaPickerDialog } from "@/features/media/media-picker-dialog";
import { cn } from "@/lib/utils";
import { API_BASE_URL, ApiError } from "@/services/api";
import { ACCEPT_ATTR, mediaApi, precheckFile } from "@/services/media";
import type { AutoDayText, DayText, ProposalOptions, ProposalSettings } from "@/types/proposal";
import { Panel, PhotoChoice } from "./designer-panels";

type Change = (patch: Partial<ProposalSettings>) => void;
const thumb = (id: number) => `${API_BASE_URL}/media/${id}/thumbnail`;

/** Upload a photo from this computer, or pick one from the image library. */
function AddPhoto({ label, onPicked }: { label: string; onPicked: (mediaId: number) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [picking, setPicking] = useState(false);
  const upload = async (file: File) => {
    const problem = precheckFile(file);
    if (problem) { toast.error(problem); return; }
    setBusy(true);
    try {
      const r = await mediaApi.upload(file, { category: "library", description: "PDF photo" });
      onPicked(r.media.id);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <button type="button" onClick={() => input.current?.click()} aria-label={`Upload a photo for ${label}`} title="Upload a photo"
        className="flex size-12 items-center justify-center rounded-md border border-dashed text-muted-foreground hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none">
        {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <ImagePlus className="size-4" aria-hidden />}
      </button>
      <button type="button" onClick={() => setPicking(true)} aria-label={`Choose from the image library for ${label}`} title="Image library"
        className="flex size-12 items-center justify-center rounded-md border border-dashed text-muted-foreground hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none">
        <Images className="size-4" aria-hidden />
      </button>
      <input ref={input} type="file" accept={ACCEPT_ATTR} className="sr-only" tabIndex={-1} aria-hidden
        onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) void upload(f); }} />
      <MediaPickerDialog open={picking} onOpenChange={setPicking} excludeIds={[]} onPick={(ids) => { if (ids[0]) onPicked(ids[0]); setPicking(false); }} />
    </>
  );
}

export function PhotosPanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  const set = (day: number, value: number | null) => {
    const next = { ...s.day_images };
    if (value === null) delete next[String(day)];
    else next[String(day)] = value;
    onChange({ day_images: next });
  };
  return (
    <Panel title="Photos" description="Upload your own photos or pick from the image library. Automatic uses the first sightseeing photo, then the hotel, then the city.">
      <div>
        <p className="mb-1 text-xs font-medium">Cover photo</p>
        <div role="radiogroup" aria-label="Cover photo" className="flex flex-wrap gap-1.5">
          <PhotoChoice on={s.cover_image === null} onClick={() => onChange({ cover_image: null })} label="Automatic"><Sparkles className="size-4" aria-hidden /></PhotoChoice>
          {s.cover_image !== null && (
            <PhotoChoice on onClick={() => undefined} label="Chosen cover photo">
              {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
              <img src={thumb(s.cover_image)} alt="" className="size-full object-cover" />
            </PhotoChoice>
          )}
          <AddPhoto label="the cover" onPicked={(id) => onChange({ cover_image: id })} />
        </div>
      </div>
      <ul className="space-y-3">
        {options.day_images.map((d) => {
          const current = s.day_images[String(d.day_number)];
          const custom = current && !d.choices.some((c) => c.media_id === current) ? current : null;
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
                {custom && (
                  <PhotoChoice on onClick={() => undefined} label="Your photo">
                    {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                    <img src={thumb(custom)} alt="" className="size-full object-cover" />
                  </PhotoChoice>
                )}
                <AddPhoto label={`day ${d.day_number}`} onPicked={(id) => set(d.day_number, id)} />
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

const EMPTY: DayText = { heading: null, subtitle: null, bullets: null, meals: null, note: null };

/** Edit the PDF wording of each day; the preview updates as you type. The itinerary itself is not changed. */
export function DayTextsPanel({ s, options, onChange }: { s: ProposalSettings; options: ProposalOptions; onChange: Change }) {
  const [open, setOpen] = useState<number | null>(null);
  const setDay = (day: number, patch: Partial<DayText> | null) => {
    const next = { ...s.day_texts };
    if (patch === null) delete next[String(day)];
    else next[String(day)] = { ...EMPTY, ...next[String(day)], ...patch };
    onChange({ day_texts: next });
  };
  return (
    <Panel title="Day-by-day text" description="Edit what each day says in the PDF. Use **double stars** for bold. The itinerary itself is not changed.">
      <ul className="space-y-1.5" aria-label="Day texts">
        {options.defaults.days.map((auto: AutoDayText) => {
          const t = s.day_texts[String(auto.day_number)];
          const edited = !!t && Object.values(t).some((v) => v !== null);
          const isOpen = open === auto.day_number;
          const id = `dt-${auto.day_number}`;
          return (
            <li key={auto.day_number} className="rounded-md border">
              <button type="button" aria-expanded={isOpen} aria-controls={id} onClick={() => setOpen(isOpen ? null : auto.day_number)}
                className="flex w-full items-center gap-2 px-2.5 py-2 text-left text-sm">
                <span className="min-w-0 flex-1 truncate"><span className="font-medium">Day {auto.day_number}</span> · {t?.heading ?? auto.heading}</span>
                {edited && <span className="rounded bg-sky-50 px-1.5 text-xs text-sky-800">edited</span>}
                <ChevronDown className={cn("size-4 transition-transform", isOpen && "rotate-180")} aria-hidden />
              </button>
              {isOpen && (
                <div id={id} className="space-y-2 border-t p-2.5">
                  <label className="block space-y-1"><span className="text-xs font-medium">Heading</span>
                    <input aria-label={`Heading for day ${auto.day_number}`} className={controlClass} value={t?.heading ?? auto.heading} maxLength={200}
                      onChange={(e) => setDay(auto.day_number, { heading: e.target.value })} />
                  </label>
                  <label className="block space-y-1"><span className="text-xs font-medium">Subtitle</span>
                    <input aria-label={`Subtitle for day ${auto.day_number}`} className={controlClass} value={t?.subtitle ?? auto.subtitle} maxLength={300}
                      onChange={(e) => setDay(auto.day_number, { subtitle: e.target.value })} />
                  </label>
                  <label className="block space-y-1"><span className="text-xs font-medium">Bullet points (one per line)</span>
                    <Textarea aria-label={`Bullet points for day ${auto.day_number}`} rows={8} value={(t?.bullets ?? auto.bullets).join("\n")}
                      onChange={(e) => setDay(auto.day_number, { bullets: e.target.value.split("\n") })} />
                  </label>
                  <label className="block space-y-1"><span className="text-xs font-medium">Meals line</span>
                    <input aria-label={`Meals for day ${auto.day_number}`} className={controlClass} value={t?.meals ?? auto.meals} maxLength={300}
                      onChange={(e) => setDay(auto.day_number, { meals: e.target.value })} />
                  </label>
                  <label className="block space-y-1"><span className="text-xs font-medium">Note (shown in italics)</span>
                    <Textarea aria-label={`Note for day ${auto.day_number}`} rows={2} value={t?.note ?? auto.note}
                      onChange={(e) => setDay(auto.day_number, { note: e.target.value })} />
                  </label>
                  {edited && (
                    <button type="button" className="inline-flex items-center gap-1 text-xs text-brand-teal hover:underline" onClick={() => setDay(auto.day_number, null)}>
                      <RotateCcw className="size-3" aria-hidden /> Back to the automatic text for this day
                    </button>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
