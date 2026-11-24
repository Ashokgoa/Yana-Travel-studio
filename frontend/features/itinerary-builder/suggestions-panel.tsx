"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { aiApi } from "@/services/ai";
import type { ItineraryDetail } from "@/types/itinerary";

type Run = (fn: () => Promise<ItineraryDetail>, success?: string) => void;

/** Reviewable improvements from inventory rules; each one is applied only when the planner clicks Apply. */
export function SuggestionsPanel({ it, run, pending }: { it: ItineraryDetail; run: Run; pending: boolean }) {
  // Re-ask after every change to the itinerary content.
  const contentKey = useMemo(() => JSON.stringify([it.days.map((d) => [d.day_number, d.activities.map((a) => a.attraction_id ?? a.title), d.meals.map((m) => m.restaurant_id ?? m.arrangement)]), it.stays.map((s) => s.hotel?.id)]), [it]);
  const q = useQuery({ queryKey: ["itineraries", "suggestions", it.id, it.version_number, contentKey], queryFn: () => aiApi.suggestions(it.id), staleTime: 30_000 });
  const items = q.data ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><Lightbulb className="size-4 text-brand-gold" aria-hidden /> Suggestions</CardTitle>
        <p className="text-xs text-muted-foreground">From inventory and the customer&apos;s requirements. Nothing changes until you click Apply{it.is_locked ? "; applying starts a new working draft" : ""}.</p>
      </CardHeader>
      <CardContent>
        {q.isPending ? <p className="text-sm text-muted-foreground">Checking…</p> : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No suggestions right now.</p>
        ) : (
          <ul className="space-y-3" aria-label="Suggestions">
            {items.map((s) => (
              <li key={s.key} className="rounded-lg border p-2.5 text-sm">
                <p className="font-medium">{s.title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{s.reason}</p>
                <Button size="sm" variant="outline" className="mt-2" disabled={pending} aria-label={`Apply: ${s.title}`}
                  onClick={() => run(() => aiApi.apply(it.id, s.key), "Suggestion applied")}>Apply</Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
