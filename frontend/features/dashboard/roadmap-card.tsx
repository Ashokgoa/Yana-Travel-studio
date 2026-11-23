import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const PHASES = [
  { id: 0, name: "Project foundation", status: "done" },
  { id: 1, name: "UI foundation & CRM", status: "next" },
  { id: 2, name: "Destination inventory & images", status: "planned" },
  { id: 3, name: "Customer requirement capture", status: "planned" },
  { id: 4, name: "Itinerary engine", status: "planned" },
  { id: 5, name: "Visual itinerary builder", status: "planned" },
  { id: 6, name: "PDF designer", status: "planned" },
  { id: 7, name: "Pricing & costing", status: "planned" },
  { id: 8, name: "AI integration (optional)", status: "planned" },
] as const;

export function RoadmapCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Build progress</CardTitle>
        <CardDescription>Modules appear in the sidebar as each phase is delivered</CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="space-y-2">
          {PHASES.map((p) => (
            <li key={p.id} className="flex items-center gap-3 text-sm">
              <span
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                  p.status === "done" && "bg-success text-white",
                  p.status === "next" && "bg-brand-gold text-primary",
                  p.status === "planned" && "bg-muted text-muted-foreground",
                )}
              >
                {p.id}
              </span>
              <span className={cn(p.status === "planned" && "text-muted-foreground")}>{p.name}</span>
              {p.status === "next" && <span className="ml-auto text-xs font-medium text-brand-teal">Next</span>}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
