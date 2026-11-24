"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Columns3, Loader2, Sparkles } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CreateItineraryButton } from "@/features/itinerary-builder/create-itinerary";
import { FromTemplateButton } from "@/features/templates/template-dialogs";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { ErrorState, TableSkeleton } from "@/components/common/states";
import { ItineraryCard } from "@/features/itineraries/parts";
import { ApiError } from "@/services/api";
import { requirementsApi } from "@/services/crm";
import { itinerariesApi } from "@/services/itineraries";

export function useGenerate(enquiryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => itinerariesApi.generate(enquiryId),
    onSuccess: (items) => {
      queryClient.setQueryData(["itineraries", "enquiry", enquiryId], items);
      queryClient.invalidateQueries({ queryKey: ["itineraries"] });
      toast.success(`${items.length} itinerary alternatives generated`);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Generation failed. Please try again.", { duration: 10_000 }),
  });
}

/** Wizard step for each missing item (see RequirementService readiness). */
function stepFor(item: string): number {
  if (item.startsWith("Budget")) return 8;
  if (item.startsWith("At least one destination")) return 3;
  return 2; // dates and airports
}

/** Why "Generate" is disabled, with a direct link to the step that needs it. */
function MissingRequirements({ enquiryId, missing, exists }: { enquiryId: number; missing: string[]; exists: boolean }) {
  const first = missing[0];
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">
      <p className="font-medium">Automatic suggestions need these customer requirements (you can still create an itinerary by hand):</p>
      {exists && missing.length ? (
        <ul className="mt-1 list-disc pl-5">{missing.map((m) => <li key={m}>{m}</li>)}</ul>
      ) : (
        <p className="mt-1">Dates, arrival and departure airports or cities, and at least one destination. A budget is optional and can be added later.</p>
      )}
      <Link href={`/crm/enquiries/${enquiryId}/requirements${first ? `?step=${stepFor(first)}` : ""}`} className={cn(buttonVariants({ size: "sm", variant: "outline" }), "mt-3 bg-background")}>
        {first ? `Add ${first.toLowerCase()}` : "Capture requirements"}
      </Link>
    </div>
  );
}

export function EnquiryItineraries({ enquiryId }: { enquiryId: number }) {
  const req = useQuery({ queryKey: ["requirements", enquiryId], queryFn: () => requirementsApi.get(enquiryId) });
  const list = useQuery({ queryKey: ["itineraries", "enquiry", enquiryId], queryFn: () => itinerariesApi.forEnquiry(enquiryId) });
  const generate = useGenerate(enquiryId);
  const [confirm, setConfirm] = useState(false);

  const latestBatch = list.data?.length ? Math.max(...list.data.map((i) => i.batch)) : 0;
  const latest = (list.data ?? []).filter((i) => i.batch === latestBatch);
  const ready = req.data?.exists && req.data.is_complete;

  const generateButton = (
    <Button variant="outline" onClick={() => (latest.length ? setConfirm(true) : generate.mutate())} disabled={!ready || generate.isPending}
      title={!ready ? "Automatic suggestions need complete customer requirements" : "Let the app propose Classic, Scenic and Premium alternatives"}>
      {generate.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <Sparkles aria-hidden />}
      Suggest itineraries
    </Button>
  );

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        <div>
          <CardTitle>Itineraries</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Plan day by day with <strong>Create itinerary</strong>, start <strong>from a template</strong>, or let the app <strong>suggest</strong> three alternatives to edit.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {latest.length > 1 && (
            <Link href={`/crm/enquiries/${enquiryId}/itineraries`} className={buttonVariants({ variant: "outline" })}>
              <Columns3 aria-hidden /> Compare
            </Link>
          )}
          <CreateItineraryButton enquiryId={enquiryId} />
          <FromTemplateButton enquiryId={enquiryId} />
          {generateButton}
        </div>
      </CardHeader>
      <CardContent>
        {list.isPending || req.isPending ? (
          <TableSkeleton rows={2} />
        ) : list.isError ? (
          <ErrorState message={list.error.message} onRetry={() => list.refetch()} />
        ) : latest.length === 0 ? (
          <div className="space-y-3">
            <p className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
              No itinerary yet. Click <strong>Create itinerary</strong> to plan it day by day: cities, overnight stays, sightseeing, restaurants and hotels.
            </p>
            {!ready && <MissingRequirements enquiryId={enquiryId} missing={req.data?.missing ?? []} exists={!!req.data?.exists} />}
          </div>
        ) : (
          <>
            {generate.isPending && <p className="mb-3 flex items-center gap-2 text-sm text-muted-foreground" role="status"><Loader2 className="size-4 animate-spin" aria-hidden /> Generating…</p>}
            <div className="grid gap-4 lg:grid-cols-3">{(list.data ?? []).map((it) => <ItineraryCard key={it.id} it={it} />)}</div>
          </>
        )}
      </CardContent>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Generate new alternatives?"
        description="A new set of three itineraries will be created from the current requirements and inventory. The existing ones are kept."
        confirmLabel="Generate"
        pending={generate.isPending}
        onConfirm={() => { setConfirm(false); generate.mutate(); }}
      />
    </Card>
  );
}
