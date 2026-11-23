import { cn } from "@/lib/utils";

const pill = "inline-flex items-center rounded-full px-2 py-0.5 font-sans text-[11px] font-semibold tracking-wide whitespace-nowrap ring-1 ring-inset";

/** PRD Part 21: fictional sample records must be clearly labelled. */
export function DemoBadge({ className }: { className?: string }) {
  return (
    <span className={cn(pill, "bg-violet-50 text-violet-700 ring-violet-600/20", className)} title="Fictional demonstration data, not real supplier information">
      DEMO
    </span>
  );
}

/** Tri-state value display: verified yes / verified no / unknown (never assumed). */
export function TriState({ value }: { value: unknown }) {
  if (value === true) return <span className="font-medium text-emerald-700">Yes (verified)</span>;
  if (value === false) return <span className="text-muted-foreground">No</span>;
  return <span className="text-amber-700">Unknown, not verified</span>;
}
