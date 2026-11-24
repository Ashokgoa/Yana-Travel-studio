import Link from "next/link";
import { AlertTriangle, Landmark, Mountain, Gem, PencilRuler, Route as RouteIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ItinerarySummary, RouteStop, Strategy } from "@/types/itinerary";

export const STRATEGY_META: Record<Strategy, { label: string; icon: typeof Landmark; className: string; accent: string }> = {
  classic: { label: "Classic", icon: Landmark, className: "bg-sky-50 text-sky-800 ring-sky-600/20", accent: "border-t-sky-500" },
  scenic: { label: "Scenic", icon: Mountain, className: "bg-emerald-50 text-emerald-800 ring-emerald-600/20", accent: "border-t-emerald-500" },
  premium: { label: "Premium", icon: Gem, className: "bg-amber-50 text-amber-800 ring-amber-600/25", accent: "border-t-brand-gold" },
  custom: { label: "Day by day", icon: PencilRuler, className: "bg-violet-50 text-violet-800 ring-violet-600/20", accent: "border-t-violet-500" },
};

export function StrategyBadge({ strategy }: { strategy: Strategy }) {
  const m = STRATEGY_META[strategy];
  const Icon = m.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-sans text-xs font-semibold tracking-normal ring-1 ring-inset", m.className)}>
      <Icon className="size-3" aria-hidden /> {m.label}
    </span>
  );
}

export function EstimateNote({ className }: { className?: string }) {
  return <span className={cn("text-[11px] font-medium text-amber-700", className)}>estimate</span>;
}

/** Offline route sketch from city coordinates (no map tiles, works without internet). */
export function RouteMap({ route, className }: { route: RouteStop[]; className?: string }) {
  const pts = route.filter((s) => s.lat !== null && s.lng !== null) as (RouteStop & { lat: number; lng: number })[];
  if (pts.length === 0) return null;
  const meanLat = pts.reduce((a, p) => a + p.lat, 0) / pts.length;
  const k = Math.cos((meanLat * Math.PI) / 180);
  const xs = pts.map((p) => p.lng * k), ys = pts.map((p) => -p.lat);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const W = 360, H = 220, padX = 46, padTop = 34, padBottom = 30;
  // Uniform scale that fits both directions (keeps geography undistorted).
  const scale = Math.min((W - 2 * padX) / Math.max(maxX - minX, 0.01), (H - padTop - padBottom) / Math.max(maxY - minY, 0.01), 160);
  const offX = (W - (maxX - minX) * scale) / 2;
  const offY = padTop + (H - padTop - padBottom - (maxY - minY) * scale) / 2;
  const P = pts.map((p, i) => ({ ...p, x: offX + (xs[i] - minX) * scale, y: offY + (ys[i] - minY) * scale }));
  // Labels: above the marker, unless that would collide with an earlier label (then below).
  const placed: { x: number; y: number }[] = [];
  const labelY = P.map((p) => {
    const above = p.y - 16, below = p.y + 26;
    const clash = (y: number) => placed.some((q) => Math.abs(q.x - p.x) < 70 && Math.abs(q.y - y) < 13);
    const y = !clash(above) && above > 10 ? above : !clash(below) && below < H - 4 ? below : above;
    placed.push({ x: p.x, y });
    return y;
  });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={cn("w-full rounded-xl bg-accent/40", className)} role="img"
      aria-label={`Route map: ${route.map((s) => `${s.city} ${s.nights} nights`).join(", ")}`}>
      <polyline points={P.map((p) => `${p.x},${p.y}`).join(" ")} fill="none" stroke="var(--brand-teal)" strokeWidth="2.5" strokeDasharray="6 4" strokeLinecap="round" />
      {P.map((p, i) => (
        <g key={`${p.city_id}-${i}`}>
          <circle cx={p.x} cy={p.y} r="11" fill="var(--brand-navy)" stroke="white" strokeWidth="2" />
          <text x={p.x} y={p.y + 3.5} textAnchor="middle" fontSize="10" fontWeight="700" fill="white">{i + 1}</text>
          <text x={p.x} y={labelY[i]} textAnchor="middle" fontSize="10.5" fontWeight="600" fill="var(--foreground)"
            stroke="var(--background)" strokeWidth="3" paintOrder="stroke">{p.city} · {p.nights}N</text>
        </g>
      ))}
    </svg>
  );
}

export function RouteChips({ route }: { route: RouteStop[] }) {
  return (
    <ol className="flex flex-wrap items-center gap-1.5 text-sm" aria-label="Route">
      {route.map((s, i) => (
        <li key={`${s.city_id}-${i}`} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-muted-foreground" aria-hidden>→</span>}
          <span className="rounded-md bg-muted px-2 py-0.5">{s.city} <span className="text-xs text-muted-foreground">{s.nights}N</span></span>
        </li>
      ))}
    </ol>
  );
}

export function avgStars(s: ItinerarySummary) {
  const stars = s.hotels.filter((h) => h?.stars).map((h) => h!.stars!);
  return stars.length ? (stars.reduce((a, b) => a + b, 0) / stars.length).toFixed(1) : "—";
}

export function ItineraryCard({ it }: { it: ItinerarySummary }) {
  const meta = STRATEGY_META[it.strategy];
  const countries = [...new Set(it.route.map((r) => r.country))];
  return (
    <Card className={cn("flex h-full flex-col border-t-4", meta.accent)}>
      <CardContent className="flex flex-1 flex-col gap-4 pt-5">
        <div className="flex items-start justify-between gap-2">
          <StrategyBadge strategy={it.strategy} />
          {it.warnings_count > 0 && (
            <span className="inline-flex items-center gap-1 text-xs text-amber-700"><AlertTriangle className="size-3.5" aria-hidden />{it.warnings_count} to check</span>
          )}
        </div>
        <p className="text-sm text-muted-foreground">{it.strategy_summary}</p>
        <RouteMap route={it.route} />
        <dl className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-muted/50 p-2"><dt className="text-[11px] text-muted-foreground">Days</dt><dd className="font-heading text-lg font-semibold">{it.total_days}</dd></div>
          <div className="rounded-lg bg-muted/50 p-2"><dt className="text-[11px] text-muted-foreground">Countries</dt><dd className="font-heading text-lg font-semibold">{countries.length}</dd></div>
          <div className="rounded-lg bg-muted/50 p-2"><dt className="text-[11px] text-muted-foreground">Hotels ★</dt><dd className="font-heading text-lg font-semibold">{avgStars(it)}</dd></div>
        </dl>
        <div>
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Estimated cost</p>
          <p className="font-heading text-2xl font-semibold">
            {formatMoney(it.cost_per_person, it.currency)} <span className="font-sans text-sm font-normal text-muted-foreground">per person</span>
          </p>
          <p className="text-xs text-muted-foreground">
            {formatMoney(it.total_cost, it.currency)} total · <EstimateNote />
            {it.unknown_cost_items > 0 && ` · ${it.unknown_cost_items} item${it.unknown_cost_items === 1 ? "" : "s"} unpriced`}
          </p>
        </div>
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><RouteIcon className="size-3.5" aria-hidden />≈ {it.total_distance_km.toLocaleString()} km by road (estimate)</p>
        <Link href={`/itineraries/${it.id}`} className="mt-auto inline-flex h-9 items-center justify-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/85">
          View day by day
        </Link>
      </CardContent>
    </Card>
  );
}
