import type { Metadata } from "next";
import { RoadmapCard } from "@/features/dashboard/roadmap-card";
import { SystemStatusCard } from "@/features/dashboard/system-status-card";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <section className="relative overflow-hidden rounded-2xl bg-primary px-8 py-10 text-primary-foreground">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 -top-20 size-72 rounded-full bg-brand-teal/40 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-24 right-40 size-56 rounded-full bg-brand-gold/25 blur-3xl"
        />
        <p className="text-xs font-medium uppercase tracking-[0.25em] text-brand-gold">YANA DMC</p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">YANA Travel Studio</h1>
        <p className="mt-3 max-w-xl text-sm text-primary-foreground/75 sm:text-base">
          Turn travel-agent requirements into tailored European itineraries and branded proposals.
        </p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <SystemStatusCard />
        <RoadmapCard />
      </div>
    </div>
  );
}
