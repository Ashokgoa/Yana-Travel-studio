"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check, ChevronLeft, ChevronRight, Loader2, Save, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, TableSkeleton } from "@/components/common/states";
import { STEPS } from "@/features/requirements/labels";
import { applySuggestions } from "@/features/requirements/apply-suggestions";
import { ReadEmailDialog } from "@/features/requirements/read-email-dialog";
import { ReadinessList, RequirementsSummary } from "@/features/requirements/requirements-summary";
import {
  StepBudget, StepDestinations, StepFood, StepHotels, StepInterests, StepNotes, StepTransport, StepTravel, StepTravellers,
  type StepProps,
} from "@/features/requirements/steps";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { enquiriesApi, requirementsApi } from "@/services/crm";
import type { EnquiryDetail } from "@/types/crm";
import type { Requirement, RequirementInput, RequirementOptions } from "@/types/requirements";

const STEP_COMPONENTS: Record<number, (p: StepProps) => React.ReactNode> = {
  1: StepTravellers, 2: StepTravel, 3: StepDestinations, 4: StepInterests, 5: StepHotels,
  6: StepFood, 7: StepTransport, 8: StepBudget, 9: StepNotes,
};
const REVIEW = 10;

function toInput(r: Requirement): RequirementInput {
  const { destinations, ...rest } = r;
  const input: RequirementInput = {
    adults: rest.adults, children: rest.children, children_ages: rest.children_ages,
    arrival_date: rest.arrival_date, departure_date: rest.departure_date, arrival_airport: rest.arrival_airport, departure_airport: rest.departure_airport,
    start_country_id: rest.start_country_id, end_country_id: rest.end_country_id, travel_type: rest.travel_type, group_size: rest.group_size,
    interests: rest.interests, travel_pace: rest.travel_pace, hotel_categories: rest.hotel_categories, hotel_locations: rest.hotel_locations,
    breakfast_required: rest.breakfast_required, rooms: rest.rooms, food_preferences: rest.food_preferences, meals: rest.meals,
    transport_modes: rest.transport_modes, passenger_capacity: rest.passenger_capacity, luggage_notes: rest.luggage_notes,
    airport_transfers: rest.airport_transfers, local_sightseeing_transport: rest.local_sightseeing_transport,
    budget_per_person: rest.budget_per_person, budget_total: rest.budget_total, currency: rest.currency,
    budget_flexibility: rest.budget_flexibility, travel_class: rest.travel_class,
    additional_requirements: rest.additional_requirements, internal_notes: rest.internal_notes, completed_steps: rest.completed_steps,
    destinations: destinations.map((d) => ({ country_id: d.country.id, city_id: d.city?.id ?? null, preference: d.preference, min_nights: d.min_nights })),
  };
  return input;
}

export function RequirementsWizard({ enquiryId }: { enquiryId: number }) {
  const enquiry = useQuery({ queryKey: ["enquiries", "detail", enquiryId], queryFn: () => enquiriesApi.get(enquiryId) });
  const requirement = useQuery({ queryKey: ["requirements", enquiryId], queryFn: () => requirementsApi.get(enquiryId), refetchOnWindowFocus: false });
  const options = useQuery({ queryKey: ["requirements", "options"], queryFn: requirementsApi.options, staleTime: Infinity });

  if (enquiry.isError || requirement.isError || options.isError) {
    const err = enquiry.error ?? requirement.error ?? options.error;
    return <ErrorState message={err?.message ?? "Could not load"} onRetry={() => { enquiry.refetch(); requirement.refetch(); options.refetch(); }} />;
  }
  if (!enquiry.data || !requirement.data || !options.data) return <TableSkeleton rows={8} />;
  // Remount the editor when a different saved version arrives from elsewhere.
  return <WizardBody key={enquiryId} enquiry={enquiry.data} initial={requirement.data} options={options.data} />;
}

function WizardBody({ enquiry, initial, options }: { enquiry: EnquiryDetail; initial: Requirement; options: RequirementOptions }) {
  const router = useRouter();
  const search = useSearchParams();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState<Requirement>(initial);
  const [draft, setDraft] = useState<RequirementInput>(() => toInput(initial));
  const [step, setStep] = useState<number>(() => {
    const fromUrl = Number(search.get("step"));
    if (fromUrl >= 1 && fromUrl <= REVIEW) return fromUrl;
    return STEPS.find((s) => s.n < REVIEW && !initial.completed_steps.includes(s.n))?.n ?? REVIEW;
  });
  const [serverError, setServerError] = useState<string | null>(null);
  const [reading, setReading] = useState(false);

  const savedInput = useMemo(() => JSON.stringify(toInput(saved)), [saved]);
  const dirty = JSON.stringify({ ...draft, completed_steps: [] }) !== JSON.stringify({ ...JSON.parse(savedInput), completed_steps: [] });

  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const save = useMutation({
    mutationFn: (body: RequirementInput) => requirementsApi.save(enquiry.id, body),
    onSuccess: (r) => {
      setSaved(r);
      // Adopt the server's normalised values (e.g. "3000" -> "3000.00", sorted meals),
      // otherwise the form would look "unsaved" right after saving.
      setDraft(toInput(r));
      setServerError(null);
      queryClient.setQueryData(["requirements", enquiry.id], r);
      queryClient.invalidateQueries({ queryKey: ["enquiries"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => {
      const msg = e instanceof ApiError
        ? (e.body?.details?.length ? e.body.details.map((d) => d.message).join(" ") : e.message)
        : "Could not save. Please try again.";
      setServerError(msg);
      toast.error(msg);
    },
  });

  const persist = async (markStep: number | null, then?: () => void) => {
    const completed = markStep ? [...new Set([...draft.completed_steps, markStep])] : draft.completed_steps;
    try {
      await save.mutateAsync({ ...draft, completed_steps: completed });
      then?.();
    } catch {
      /* error shown via onError */
    }
  };

  const goto = (n: number) => {
    setStep(n);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const set = (patch: Partial<RequirementInput>) => setDraft((d) => ({ ...d, ...patch }));
  const StepComponent = STEP_COMPONENTS[step];
  const meta = STEPS.find((s) => s.n === step)!;
  const nights = draft.arrival_date && draft.departure_date ? Math.round((Date.parse(draft.departure_date) - Date.parse(draft.arrival_date)) / 86_400_000) : null;
  const doneCount = saved.completed_steps.length;

  return (
    <>
      <PageHeader
        back={{ href: `/crm/enquiries/${enquiry.id}`, label: enquiry.reference }}
        title="Customer requirements"
        description={`${enquiry.customer.name} · via ${enquiry.travel_agent.company_name}`}
        actions={
          <>
            <Button variant="outline" onClick={() => setReading(true)}><Sparkles aria-hidden /> Read from email</Button>
            <Button variant="outline" onClick={() => persist(null, () => toast.success("Draft saved"))} disabled={save.isPending}>
              {save.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <Save aria-hidden />} Save draft
            </Button>
          </>
        }
      />
      <ReadEmailDialog enquiryId={enquiry.id} open={reading} onOpenChange={setReading}
        onApply={(picked) => { set(applySuggestions(draft, picked)); toast.success(`${picked.length} item${picked.length === 1 ? "" : "s"} filled in. Check them, then save.`); }} />

      <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)] xl:grid-cols-[15rem_minmax(0,1fr)_18rem]">
        {/* Step navigation */}
        <nav aria-label="Requirement steps" className="lg:sticky lg:top-6 lg:self-start">
          <div className="mb-3 lg:hidden">
            <div className="mb-1 flex justify-between text-xs text-muted-foreground"><span>Step {Math.min(step, 9)} of 9</span><span>{doneCount}/9 saved</span></div>
            <div className="h-1.5 rounded-full bg-muted"><div className="h-1.5 rounded-full bg-brand-teal transition-all" style={{ width: `${(doneCount / 9) * 100}%` }} /></div>
          </div>
          <ol className="hidden space-y-1 lg:block">
            {STEPS.map((s) => {
              const done = saved.completed_steps.includes(s.n) || (s.n === REVIEW && saved.is_complete);
              const current = s.n === step;
              return (
                <li key={s.n}>
                  <button
                    type="button"
                    onClick={() => goto(s.n)}
                    aria-current={current ? "step" : undefined}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
                      current ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                    )}
                  >
                    <span className={cn(
                      "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                      current ? "bg-brand-gold text-primary" : done ? "bg-success text-white" : "bg-muted text-muted-foreground",
                    )}>
                      {done && !current ? <Check className="size-3.5" aria-label="completed" /> : s.n === REVIEW ? "✓" : s.n}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-medium">{s.title}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>

        {/* Current step */}
        <Card className="min-w-0">
          <CardHeader className="border-b">
            <p className="text-xs font-medium tracking-wide text-brand-teal uppercase">{step === REVIEW ? "Final step" : `Step ${step} of 9`}</p>
            <CardTitle className="text-2xl">{meta.title}</CardTitle>
            <p className="text-sm text-muted-foreground">{meta.description}</p>
          </CardHeader>
          <CardContent className="py-6">
            {serverError && (
              <div role="alert" className="mb-5 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{serverError}</div>
            )}
            {step === REVIEW ? (
              <div className="space-y-6">
                {dirty && <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">You have unsaved changes. Save to update this summary.</p>}
                <RequirementsSummary req={saved} />
                <div className="rounded-xl border p-4"><ReadinessList req={saved} /></div>
              </div>
            ) : (
              <StepComponent value={draft} set={set} options={options} enquiry={enquiry} />
            )}
          </CardContent>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t px-6 py-4">
            <Button variant="ghost" onClick={() => goto(step - 1)} disabled={step === 1}>
              <ChevronLeft aria-hidden /> Back
            </Button>
            {step === REVIEW ? (
              <div className="flex gap-2">
                {dirty && <Button variant="outline" onClick={() => persist(null)} disabled={save.isPending}>Save changes</Button>}
                <Button onClick={() => persist(null, () => { toast.success("Requirements saved"); router.push(`/crm/enquiries/${enquiry.id}`); })} disabled={save.isPending}>
                  {save.isPending && <Loader2 className="animate-spin" aria-hidden />} Finish
                </Button>
              </div>
            ) : (
              <Button onClick={() => persist(step, () => goto(step + 1))} disabled={save.isPending}>
                {save.isPending && <Loader2 className="animate-spin" aria-hidden />} Save &amp; continue <ChevronRight aria-hidden />
              </Button>
            )}
          </div>
        </Card>

        {/* Readiness */}
        <aside className="space-y-4 lg:col-span-2 xl:col-span-1 xl:sticky xl:top-6 xl:self-start" aria-label="Readiness">
          <Card>
            <CardHeader><CardTitle>Readiness</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="rounded-lg bg-muted/50 p-3"><p className="font-heading text-2xl font-semibold tabular-nums">{nights !== null && nights >= 0 ? nights + 1 : "–"}</p><p className="text-xs text-muted-foreground">days</p></div>
                <div className="rounded-lg bg-muted/50 p-3"><p className="font-heading text-2xl font-semibold tabular-nums">{draft.adults + draft.children}</p><p className="text-xs text-muted-foreground">travellers</p></div>
              </div>
              <ReadinessList req={saved} />
              <p className="text-xs text-muted-foreground">{saved.exists ? "Based on the last save." : "Not saved yet."}</p>
            </CardContent>
          </Card>
        </aside>
      </div>
    </>
  );
}
