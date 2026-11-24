"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DatabaseBackup, Download, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/states";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime } from "@/lib/format";
import { ApiError } from "@/services/api";
import { housekeepingApi, type BackupInfo, type DemoSummary } from "@/services/housekeeping";

const size = (b: number) => (b > 1_048_576 ? `${(b / 1_048_576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);
type DemoKind = "hotels" | "restaurants" | "vehicles" | "sightseeing" | "suppliers";
const DEMO_LABELS: [DemoKind, string][] = [["hotels", "Hotels"], ["restaurants", "Restaurants"], ["vehicles", "Vehicles"], ["sightseeing", "Sightseeing"], ["suppliers", "Suppliers"]];

export function DataAdmin() {
  const qc = useQueryClient();
  const backups = useQuery({ queryKey: ["admin", "backups"], queryFn: housekeepingApi.backups });
  const demo = useQuery({ queryKey: ["admin", "demo-data"], queryFn: housekeepingApi.demoSummary });
  const [deleting, setDeleting] = useState<BackupInfo | null>(null);
  const [removing, setRemoving] = useState(false);
  const create = useMutation({
    mutationFn: housekeepingApi.createBackup,
    onSuccess: (b) => { toast.success(`Backup created: ${b.name}`); void qc.invalidateQueries({ queryKey: ["admin", "backups"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Backup failed"),
  });
  const del = useMutation({
    mutationFn: (name: string) => housekeepingApi.deleteBackup(name),
    onSuccess: () => { toast.success("Backup deleted"); setDeleting(null); void qc.invalidateQueries({ queryKey: ["admin", "backups"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not delete"),
  });
  const remove = useMutation({
    mutationFn: housekeepingApi.removeDemo,
    onSuccess: (r) => {
      const deleted = Object.values(r).reduce((n, x) => n + x.deleted, 0);
      const kept = Object.values(r).reduce((n, x) => n + x.deactivated, 0);
      toast.success(`Demo data removed: ${deleted} deleted${kept ? `, ${kept} still used by itineraries kept as inactive` : ""}.`);
      setRemoving(false);
      void qc.invalidateQueries();
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not remove demo data"),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Backups & data" description="Back up and restore everything, and remove the demonstration inventory once real data is loaded." />

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
          <div>
            <CardTitle className="text-base">Backups</CardTitle>
            <p className="text-xs text-muted-foreground">Database, uploaded images and generated PDFs in one zip, kept in <code>database\backups</code> on this computer. Safe while people are working.</p>
          </div>
          <Button onClick={() => create.mutate()} disabled={create.isPending}>
            {create.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <DatabaseBackup aria-hidden />} Back up now
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {backups.error ? <ErrorState message={backups.error.message} onRetry={() => void backups.refetch()} /> : !backups.data ? <p className="text-sm text-muted-foreground">Loading…</p>
            : backups.data.length === 0 ? <p className="text-sm text-muted-foreground">No backups yet.</p> : (
              <ul className="divide-y rounded-lg border" aria-label="Backups">
                {backups.data.map((b) => (
                  <li key={b.name} className="flex flex-wrap items-center gap-3 p-3 text-sm">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{formatDateTime(b.created_at)} <span className="font-normal text-muted-foreground">· {size(b.size_bytes)}{b.created_by ? ` · ${b.created_by}` : ""}</span></p>
                      <p className="truncate text-xs text-muted-foreground" title={b.name}>
                        {b.name}{b.counts?.enquiries !== undefined ? ` · ${b.counts.enquiries} enquiries, ${b.counts.itineraries} itineraries, ${b.counts.media} images, ${b.counts.proposal_exports} PDFs` : ""}
                      </p>
                    </div>
                    <a href={housekeepingApi.backupUrl(b.name)} className={buttonVariants({ size: "sm", variant: "outline" })} aria-label={`Download ${b.name}`}><Download aria-hidden /> Download</a>
                    <Button size="sm" variant="ghost" aria-label={`Delete ${b.name}`} onClick={() => setDeleting(b)}><Trash2 aria-hidden /></Button>
                  </li>
                ))}
              </ul>
            )}
          <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">Restoring a backup</p>
            <p>Restore replaces all data, so it is done on the server, not from the browser: stop the app (close the start.ps1 windows), then run</p>
            <code className="mt-1 block rounded bg-background px-2 py-1">scripts\restore.ps1 -File database\backups\&lt;backup file&gt;.zip</code>
            <p className="mt-1">The current state is backed up automatically first. Tip: copy backups to a second, company-approved location regularly.</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Demonstration data</CardTitle>
          <p className="text-xs text-muted-foreground">The fictional hotels, restaurants, vehicles and suppliers marked DEMO. Real countries, cities and sightseeing are kept.</p>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {demo.data ? <DemoTable d={demo.data} /> : <p className="text-muted-foreground">Loading…</p>}
          <Button variant="outline" className="border-destructive/40 text-destructive hover:bg-destructive/5" disabled={!demo.data?.total || remove.isPending} onClick={() => setRemoving(true)}>
            <Trash2 aria-hidden /> Remove demo data
          </Button>
        </CardContent>
      </Card>

      <ConfirmDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)} title="Delete this backup?" description={deleting?.name ?? ""}
        confirmLabel="Delete" destructive pending={del.isPending} onConfirm={() => deleting && del.mutate(deleting.name)} />
      <ConfirmDialog open={removing} onOpenChange={setRemoving} title="Remove all demo data?"
        description="Demo records not used by any itinerary are deleted. Records used by itineraries are kept but made inactive, so no itinerary breaks. Make a backup first if unsure."
        confirmLabel="Remove demo data" destructive pending={remove.isPending} onConfirm={() => remove.mutate()} />
    </div>
  );
}

function DemoTable({ d }: { d: DemoSummary }) {
  if (!d.total) return <p className="text-muted-foreground">No active demo data.</p>;
  return (
    <table className="w-full max-w-md text-sm" aria-label="Demo data">
      <thead className="text-left text-xs text-muted-foreground"><tr><th className="py-1 font-medium">Type</th><th className="font-medium">Demo records</th><th className="font-medium">Used in itineraries</th></tr></thead>
      <tbody>
        {DEMO_LABELS.map(([k, label]) => (
          <tr key={k} className="border-t"><td className="py-1">{label}</td><td>{d[k].demo}</td><td>{d[k].in_use ?? "—"}</td></tr>
        ))}
      </tbody>
    </table>
  );
}
