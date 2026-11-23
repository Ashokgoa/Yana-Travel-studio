"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Building2, FilePlus2, UserPlus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/states";
import { useAuth } from "@/features/auth/auth-provider";
import { EnquiriesTable } from "@/features/crm/enquiries/enquiries-table";
import { RoadmapCard } from "@/features/dashboard/roadmap-card";
import { SystemStatusCard } from "@/features/dashboard/system-status-card";
import { dashboardApi } from "@/services/crm";
import type { EnquiryStatus } from "@/types/crm";

/** PRD Part 20 metrics, all derived from enquiry statuses. */
const METRICS: { label: string; statuses: EnquiryStatus[] | "all"; hint: string }[] = [
  { label: "Total enquiries", statuses: "all", hint: "All time" },
  { label: "New", statuses: ["new"], hint: "Waiting to be picked up" },
  { label: "In progress", statuses: ["in_progress", "revision_requested"], hint: "Including revisions" },
  { label: "Proposals generated", statuses: ["proposal_generated"], hint: "Ready to send" },
  { label: "Awaiting response", statuses: ["sent_to_agent"], hint: "Sent to agent" },
  { label: "Approved", statuses: ["approved"], hint: "Agent approved" },
  { label: "Confirmed bookings", statuses: ["booking_confirmed"], hint: "Confirmed" },
];

const QUICK_ACTIONS = [
  { href: "/crm/enquiries/new", label: "Create new enquiry", icon: FilePlus2 },
  { href: "/crm/agents", label: "Add travel agent", icon: Building2 },
  { href: "/crm/customers", label: "Add customer", icon: UserPlus },
];

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export function Dashboard() {
  const { user, hasRole } = useAuth();
  const summary = useQuery({ queryKey: ["dashboard", "summary"], queryFn: dashboardApi.summary });

  const metricValue = (statuses: EnquiryStatus[] | "all") => {
    if (!summary.data) return null;
    if (statuses === "all") return summary.data.total_enquiries;
    return statuses.reduce((sum, s) => sum + (summary.data.by_status[s] ?? 0), 0);
  };

  // EnquiriesTable expects a paged query shape; adapt the summary's recent list.
  const recentQuery = {
    ...summary,
    data: summary.data ? { items: summary.data.recent_enquiries, total: summary.data.recent_enquiries.length, page: 1, page_size: 6 } : undefined,
  } as Parameters<typeof EnquiriesTable>[0]["query"];

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <section className="relative overflow-hidden rounded-2xl bg-primary px-8 py-9 text-primary-foreground">
        <div aria-hidden className="pointer-events-none absolute -top-20 -right-16 size-72 rounded-full bg-brand-teal/40 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute right-40 -bottom-24 size-56 rounded-full bg-brand-gold/25 blur-3xl" />
        <p className="text-xs font-medium tracking-[0.25em] text-brand-gold uppercase">YANA Travel Studio</p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">
          {greeting()}, {user?.full_name.split(" ")[0]}
        </h1>
        <p className="mt-2 max-w-xl text-sm text-primary-foreground/75 sm:text-base">
          {summary.data
            ? `${summary.data.by_status.new} new enquir${summary.data.by_status.new === 1 ? "y" : "ies"} · ${summary.data.active_agents} active travel agents · ${summary.data.customers} customers`
            : "Loading your overview…"}
        </p>
      </section>

      {summary.isError ? (
        <ErrorState message={summary.error.message} onRetry={() => summary.refetch()} />
      ) : (
        <section aria-label="Enquiry metrics" className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
          {METRICS.map((m, i) => (
            <Card key={m.label} className={i === 0 ? "bg-accent/60" : undefined}>
              <CardContent className="py-5">
                <p className="text-xs font-medium text-muted-foreground">{m.label}</p>
                {summary.isPending ? (
                  <Skeleton className="mt-2 h-8 w-12" />
                ) : (
                  <p className="mt-1 font-heading text-3xl font-semibold tabular-nums">{metricValue(m.statuses)}</p>
                )}
                <p className="mt-1 text-[11px] text-muted-foreground">{m.hint}</p>
              </CardContent>
            </Card>
          ))}
        </section>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent enquiries</CardTitle>
            <Link href="/crm/enquiries" className="inline-flex items-center gap-1 text-sm font-medium text-brand-teal hover:underline">
              View all <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </CardHeader>
          <CardContent>
            <EnquiriesTable query={recentQuery} compact emptyText="No enquiries yet. Create the first one." />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
              {QUICK_ACTIONS.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className="group flex items-center gap-3 rounded-lg border px-3 py-3 text-sm font-medium transition-colors hover:border-brand-teal/40 hover:bg-accent"
                >
                  <span className="flex size-8 items-center justify-center rounded-md bg-accent text-accent-foreground group-hover:bg-background">
                    <Icon className="size-4" aria-hidden />
                  </span>
                  {label}
                  <ArrowRight className="ml-auto size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden />
                </Link>
              ))}
            </CardContent>
          </Card>
          {hasRole("admin") && <SystemStatusCard />}
        </div>
      </div>

      <RoadmapCard />
    </div>
  );
}
