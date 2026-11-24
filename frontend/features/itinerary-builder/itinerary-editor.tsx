"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Copy, Eye, History, Loader2, Lock, PencilLine, Save } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { controlClass, FormField } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, TableSkeleton } from "@/components/common/states";
import { StrategyBadge } from "@/features/itineraries/parts";
import { DayEditor, type DragState } from "@/features/itinerary-builder/day-editor";
import { CostSummary, HotelsPanel, LiveChecks, TransportPanel } from "@/features/itinerary-builder/side-panels";
import { detailKey, useEditor } from "@/features/itinerary-builder/use-editor";
import { VersionsDialog } from "@/features/itinerary-builder/versions-dialog";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { requirementsApi } from "@/services/crm";
import { itinerariesApi } from "@/services/itineraries";

function SaveVersionDialog({ open, onClose, onSave }: { open: boolean; onClose: () => void; onSave: (label: string, notes: string) => void }) {
  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  return (
    <FormDialog open={open} onOpenChange={(o) => !o && onClose()} title="Save version" description="Saved versions are kept read-only so you can always go back or compare." formId="save-version-form" submitLabel="Save version">
      <form id="save-version-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (label.trim()) { onSave(label.trim(), notes.trim()); setLabel(""); setNotes(""); } }}>
        <FormField label="Version name" htmlFor="sv-label" required hint="e.g. ‘Additional Switzerland day’ or ‘Hotel upgrades’">
          <input id="sv-label" className={controlClass} value={label} onChange={(e) => setLabel(e.target.value)} autoFocus maxLength={200} />
        </FormField>
        <FormField label="Notes" htmlFor="sv-notes" hint="Optional: what changed and why">
          <textarea id="sv-notes" rows={3} className={cn(controlClass, "h-auto py-2")} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={2000} />
        </FormField>
      </form>
    </FormDialog>
  );
}

export function ItineraryEditor({ id }: { id: number }) {
  const router = useRouter();
  const query = useQuery({ queryKey: detailKey(id), queryFn: () => itinerariesApi.get(id) });
  const req = useQuery({
    queryKey: ["requirements", query.data?.enquiry_id],
    queryFn: () => requirementsApi.get(query.data!.enquiry_id!),
    enabled: Boolean(query.data?.enquiry_id),
  });
  const { run, pending } = useEditor(id);
  const [drag, setDrag] = useState<DragState>(null);
  const [saving, setSaving] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const duplicate = useMutation({
    mutationFn: () => itinerariesApi.duplicate(id),
    onSuccess: (copy) => { toast.success("Itinerary duplicated"); router.push(`/itineraries/${copy.id}/edit`); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not duplicate"),
  });

  if (query.isPending) return <TableSkeleton rows={10} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const it = query.data;
  const editable = !it.is_locked;
  const stayFor = (n: number) => it.stays.find((s) => n >= s.check_in_day && n < s.check_in_day + s.nights);

  return (
    <>
      <PageHeader
        back={{ href: `/itineraries/${id}`, label: "Back to itinerary" }}
        title={<span className="flex flex-wrap items-center gap-3">Itinerary builder <StrategyBadge strategy={it.strategy} /></span>}
        description={`${it.customer_name ?? ""} · ${it.enquiry_reference ?? ""} · ${formatDate(it.start_date)} · ${it.total_days} days / ${it.total_nights} nights`}
        actions={
          <>
            <span className={cn("mr-1 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-opacity", pending ? "opacity-100" : "opacity-0")} role="status" aria-live="polite">
              <Loader2 className="size-3.5 animate-spin" aria-hidden /> Saving…
            </span>
            <Button variant="outline" onClick={() => setShowVersions(true)}><History aria-hidden /> Versions</Button>
            <Button variant="outline" onClick={() => duplicate.mutate()} disabled={duplicate.isPending}><Copy aria-hidden /> Duplicate</Button>
            <Link href={`/itineraries/${id}`} className={buttonVariants({ variant: "outline" })}><Eye aria-hidden /> View</Link>
            {editable && <Button onClick={() => setSaving(true)}><Save aria-hidden /> Save version</Button>}
          </>
        }
      />

      {editable ? (
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-brand-gold/40 bg-amber-50/60 px-4 py-3 text-sm">
          <PencilLine className="size-4 text-amber-700" aria-hidden />
          <span>Editing <strong>version {it.version_number}</strong> ({it.version_label}). Changes are stored as you go; use <strong>Save version</strong> to keep a named snapshot.</span>
        </div>
      ) : (
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border bg-muted/50 px-4 py-3 text-sm">
          <Lock className="size-4 text-muted-foreground" aria-hidden />
          <span className="flex-1">Version {it.version_number} (<strong>{it.version_label}</strong>) is saved and read-only. Editing creates a working copy; this version stays unchanged.</span>
          <Button onClick={() => run(() => itinerariesApi.startEditing(id), "Working copy created")} disabled={pending}><PencilLine aria-hidden /> Start editing</Button>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section aria-label="Days" className={cn("space-y-4", pending && "pointer-events-none opacity-80")}>
          <nav aria-label="Jump to day" className="flex flex-wrap gap-1.5">
            {it.days.map((d) => <a key={d.id} href={`#day-${d.day_number}`} className="rounded-md bg-muted px-2 py-1 text-xs hover:bg-accent">Day {d.day_number}</a>)}
          </nav>
          {editable && <p className="text-xs text-muted-foreground">Tip: drag activities by the handle, or use the arrows (at the top/bottom of a day they move to the previous/next day).</p>}
          {it.days.map((d) => (
            <DayEditor key={d.id} it={it} day={d} stay={stayFor(d.day_number)} editable={editable} run={run} drag={drag} setDrag={setDrag}
              foodPreferences={req.data?.food_preferences ?? []} />
          ))}
        </section>
        <div className="space-y-6 xl:sticky xl:top-6 xl:max-h-[calc(100vh-3rem)] xl:self-start xl:overflow-y-auto">
          <CostSummary it={it} />
          <LiveChecks it={it} />
          <HotelsPanel it={it} editable={editable} run={run} />
          <TransportPanel it={it} editable={editable} run={run} />
        </div>
      </div>

      <SaveVersionDialog open={saving} onClose={() => setSaving(false)}
        onSave={(label, notes) => { setSaving(false); run(() => itinerariesApi.saveVersion(id, label, notes || undefined), `Saved as version ${it.version_number}: ${label}`); }} />
      <VersionsDialog it={it} open={showVersions} onOpenChange={setShowVersions} run={run} />
    </>
  );
}
