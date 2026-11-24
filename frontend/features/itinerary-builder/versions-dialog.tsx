"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { GitCompare, Lock, PencilLine, RotateCcw } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { NativeSelect } from "@/components/common/form-controls";
import { formatDateTime, formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { itinerariesApi } from "@/services/itineraries";
import type { ItineraryDetail } from "@/types/itinerary";

export function VersionsDialog({
  it, open, onOpenChange, run,
}: { it: ItineraryDetail; open: boolean; onOpenChange: (o: boolean) => void; run: (fn: () => Promise<ItineraryDetail>, success?: string) => void }) {
  const versions = useQuery({ queryKey: ["itineraries", "versions", it.id], queryFn: () => itinerariesApi.versions(it.id), enabled: open });
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<number | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);
  const list = versions.data ?? [];
  const va = a ?? list[1]?.version_number ?? list[0]?.version_number ?? null;
  const vb = b ?? list[0]?.version_number ?? null;
  const diff = useQuery({
    queryKey: ["itineraries", "versions", it.id, "compare", va, vb],
    queryFn: () => itinerariesApi.compare(it.id, va!, vb!),
    enabled: open && va !== null && vb !== null && va !== vb,
  });

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Versions</DialogTitle>
            <DialogDescription>Saved versions are read-only. Restoring copies a version into a new working draft; nothing is overwritten.</DialogDescription>
          </DialogHeader>
          <ul className="divide-y rounded-xl border">
            {list.map((v) => (
              <li key={v.version_number} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold", v.is_locked ? "bg-muted" : "bg-brand-gold text-primary")}>v{v.version_number}</span>
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-1.5 font-medium">
                    {v.is_locked ? <Lock className="size-3.5 text-muted-foreground" aria-label="Saved, read-only" /> : <PencilLine className="size-3.5 text-brand-teal" aria-label="Working draft" />}
                    {v.label}
                    {v.version_number === it.version_number && <span className="text-xs font-normal text-muted-foreground">(open)</span>}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {v.total_days} days · {formatMoney(v.total_cost, v.currency)} est. · {formatDateTime(v.created_at)}{v.created_by ? ` · ${v.created_by}` : ""}
                  </p>
                  {v.notes && <p className="text-xs text-muted-foreground">{v.notes}</p>}
                </div>
                <Link href={`/itineraries/${it.id}?version=${v.version_number}`} className={buttonVariants({ variant: "ghost", size: "sm" })} onClick={() => onOpenChange(false)}>View</Link>
                {v.version_number !== list[0]?.version_number || v.is_locked ? (
                  <Button size="sm" variant="outline" onClick={() => setRestoring(v.version_number)}><RotateCcw aria-hidden /> Restore</Button>
                ) : null}
              </li>
            ))}
          </ul>
          {list.length > 1 && (
            <div className="space-y-3 rounded-xl bg-muted/40 p-4">
              <p className="flex items-center gap-2 text-sm font-medium"><GitCompare className="size-4" aria-hidden /> Compare versions</p>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <NativeSelect aria-label="Compare from version" className="w-44" value={va ?? ""} onChange={(e) => setA(Number(e.target.value))}>
                  {list.map((v) => <option key={v.version_number} value={v.version_number}>v{v.version_number} · {v.label}</option>)}
                </NativeSelect>
                <span>→</span>
                <NativeSelect aria-label="Compare to version" className="w-44" value={vb ?? ""} onChange={(e) => setB(Number(e.target.value))}>
                  {list.map((v) => <option key={v.version_number} value={v.version_number}>v{v.version_number} · {v.label}</option>)}
                </NativeSelect>
              </div>
              {va === vb ? <p className="text-sm text-muted-foreground">Choose two different versions.</p> : diff.data ? (
                <ul className="list-disc space-y-1 pl-5 text-sm" aria-live="polite">{diff.data.summary.map((s, i) => <li key={i}>{s}</li>)}</ul>
              ) : <p className="text-sm text-muted-foreground">Comparing…</p>}
            </div>
          )}
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={restoring !== null}
        onOpenChange={(o) => !o && setRestoring(null)}
        title={`Restore version ${restoring}?`}
        description={`A new working draft is created as a copy of version ${restoring}.${!it.is_locked ? " Your current unsaved draft is kept as a saved version first." : ""}`}
        confirmLabel="Restore"
        onConfirm={() => { const n = restoring!; setRestoring(null); onOpenChange(false); run(() => itinerariesApi.restore(it.id, n), `Version ${n} restored as a new draft`); }}
      />
    </>
  );
}
