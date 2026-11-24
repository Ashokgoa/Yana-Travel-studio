"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookmarkPlus, LayoutTemplate, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { FormField, controlClass } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { housekeepingApi } from "@/services/housekeeping";

/** "Save as template" on an itinerary. */
export function SaveAsTemplateButton({ id, version, defaultTitle }: { id: number; version?: number; defaultTitle: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState("");
  const save = useMutation({
    mutationFn: () => housekeepingApi.saveAsTemplate(id, { title, description: description || null }, version),
    onSuccess: (t) => { toast.success(`Template saved: ${t.title}`); setOpen(false); void qc.invalidateQueries({ queryKey: ["itinerary-templates"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save the template"),
  });
  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}><BookmarkPlus aria-hidden /> Save as template</Button>
      <FormDialog open={open} onOpenChange={setOpen} title="Save as template" formId="tpl-form" submitLabel="Save template" pending={save.isPending}
        description="A read-only copy for reuse with other enquiries. Dates are moved and hotel rooms re-priced when it is used.">
        <form id="tpl-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (title.trim().length >= 2) save.mutate(); }}>
          <FormField label="Template name" htmlFor="tpl-title" required>
            <input id="tpl-title" className={controlClass} maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. European Grand Tour, 12 days" />
          </FormField>
          <FormField label="Description" htmlFor="tpl-desc">
            <Textarea id="tpl-desc" rows={3} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Who it suits, season, notes" />
          </FormField>
        </form>
      </FormDialog>
    </>
  );
}

/** "From a template" on an enquiry: pick a template, create an itinerary starting on the customer's arrival date. */
export function FromTemplateButton({ enquiryId }: { enquiryId: number }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState<number | null>(null);
  const list = useQuery({ queryKey: ["itinerary-templates"], queryFn: housekeepingApi.templates, enabled: open });
  const create = useMutation({
    mutationFn: () => housekeepingApi.fromTemplate(enquiryId, picked!),
    onSuccess: (it) => {
      toast.success("Itinerary created from the template");
      void qc.invalidateQueries({ queryKey: ["itineraries"] });
      router.push(`/itineraries/${it.id}`);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not create the itinerary"),
  });
  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}><LayoutTemplate aria-hidden /> From a template</Button>
      <FormDialog open={open} onOpenChange={setOpen} title="Start from a template" formId="from-tpl-form" submitLabel="Create itinerary" pending={create.isPending}
        description="The itinerary is copied and moved to the customer's arrival date; hotel rooms are re-priced for the new dates. Check travellers and rooms afterwards." wide>
        <form id="from-tpl-form" onSubmit={(e) => { e.preventDefault(); if (picked) create.mutate(); }}>
          {list.isPending ? <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" aria-hidden /> Loading…</p>
            : !list.data?.length ? <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No templates yet. Open a good itinerary and click “Save as template”.</p> : (
              <ul role="radiogroup" aria-label="Templates" className="max-h-96 space-y-2 overflow-y-auto pr-1">
                {list.data.map((t) => (
                  <li key={t.id}>
                    <button type="button" role="radio" aria-checked={picked === t.id} onClick={() => setPicked(t.id)}
                      className={cn("w-full rounded-lg border p-2.5 text-left text-sm transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                        picked === t.id ? "border-brand-teal bg-accent" : "hover:bg-muted/60")}>
                      <span className="block font-medium">{t.title}</span>
                      <span className="block text-xs text-muted-foreground">{t.total_days} days · {t.route.map((r) => r.city).join(" → ")}</span>
                      {t.version_notes && <span className="block text-xs text-muted-foreground">{t.version_notes}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
        </form>
      </FormDialog>
    </>
  );
}

