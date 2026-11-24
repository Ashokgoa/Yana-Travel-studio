"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Eye, LayoutTemplate } from "lucide-react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { ApiError } from "@/services/api";
import { housekeepingApi } from "@/services/housekeeping";
import type { ItinerarySummary } from "@/types/itinerary";

export function TemplatesPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["itinerary-templates"], queryFn: housekeepingApi.templates });
  const [archiving, setArchiving] = useState<ItinerarySummary | null>(null);
  const archive = useMutation({
    mutationFn: (id: number) => housekeepingApi.archiveTemplate(id),
    onSuccess: () => { toast.success("Template archived"); setArchiving(null); void qc.invalidateQueries({ queryKey: ["itinerary-templates"] }); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not archive"),
  });
  return (
    <>
      <PageHeader title="Itinerary Templates" description="Proven itineraries to reuse. Save one from any itinerary (“Save as template”), then use it from an enquiry (“From a template”)." />
      <Card className="p-4 sm:p-5">
        {list.isPending ? <TableSkeleton /> : list.isError ? <ErrorState message={list.error.message} onRetry={() => list.refetch()} /> : list.data.length === 0 ? (
          <EmptyState icon={LayoutTemplate} title="No templates yet" description="Open a good itinerary and click “Save as template”." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Template</TableHead><TableHead className="hidden lg:table-cell">Route</TableHead><TableHead>Days</TableHead><TableHead className="hidden md:table-cell">Saved</TableHead><TableHead className="text-right">Actions</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>
                    <div className="font-medium">{t.title}</div>
                    {t.version_notes && <div className="text-xs text-muted-foreground">{t.version_notes}</div>}
                  </TableCell>
                  <TableCell className="hidden max-w-md truncate text-sm lg:table-cell">{t.route.map((r) => r.city).join(" → ")}</TableCell>
                  <TableCell>{t.total_days}</TableCell>
                  <TableCell className="hidden text-sm md:table-cell">{formatDate(t.created_at)}</TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <Link href={`/itineraries/${t.id}`} className={buttonVariants({ size: "sm", variant: "ghost" })} aria-label={`View ${t.title}`}><Eye aria-hidden /> View</Link>
                    <Button size="sm" variant="ghost" onClick={() => setArchiving(t)} aria-label={`Archive ${t.title}`}><Archive aria-hidden /> Archive</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
      <ConfirmDialog open={!!archiving} onOpenChange={(o) => !o && setArchiving(null)} title={`Archive “${archiving?.title ?? ""}”?`}
        description="It will no longer be offered for new itineraries. Itineraries already created from it are not affected."
        confirmLabel="Archive" destructive pending={archive.isPending} onConfirm={() => archiving && archive.mutate(archiving.id)} />
    </>
  );
}
