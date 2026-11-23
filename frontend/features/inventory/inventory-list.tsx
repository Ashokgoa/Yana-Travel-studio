"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { NativeSelect } from "@/components/common/form-controls";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states";
import { ActiveBadge } from "@/components/common/status-badge";
import { useAuth } from "@/features/auth/auth-provider";
import { DemoBadge } from "@/features/inventory/badges";
import { InventoryFormDialog } from "@/features/inventory/inventory-form-dialog";
import { humanize, RESOURCES, type FilterDef } from "@/features/inventory/resource-config";
import { useInventoryOptions, useRefOptions } from "@/features/inventory/use-inventory-data";
import { inventoryApi } from "@/services/inventory";
import type { InventoryItem, ResourceKey } from "@/types/inventory";

const PAGE_SIZE = 20;

export function Thumb({ item, icon: Icon, size = "size-10" }: { item: InventoryItem; icon: React.ComponentType<{ className?: string }>; size?: string }) {
  return item.primary_image_url ? (
    // eslint-disable-next-line @next/next/no-img-element -- served by our API (auth cookie), not optimisable by next/image
    <img src={item.primary_image_url} alt="" className={`${size} shrink-0 rounded-lg object-cover`} loading="lazy" />
  ) : (
    <span className={`${size} flex shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground`}>
      <Icon className="size-4" aria-hidden />
    </span>
  );
}

function FilterSelect({ filter, value, onChange }: { filter: FilterDef; value: string; onChange: (v: string) => void }) {
  const { data: options } = useInventoryOptions();
  const refs = useRefOptions(filter.ref);
  const choices = filter.staticOptions
    ? filter.staticOptions
    : filter.vocab && options
      ? (options[filter.vocab] as string[]).map((v) => [v, humanize(v)] as [string, string])
      : (refs.data ?? []).map((o) => [o.value, o.label] as [string, string]);
  return (
    <NativeSelect aria-label={filter.label} value={value} onChange={(e) => onChange(e.target.value)} className="sm:w-48">
      <option value="">{filter.label}</option>
      {choices.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </NativeSelect>
  );
}

export function InventoryList({ resource }: { resource: ResourceKey }) {
  const config = RESOURCES[resource];
  const router = useRouter();
  const { hasRole } = useAuth();
  const isAdmin = hasRole("admin");
  const [q, setQ] = useState("");
  const [active, setActive] = useState("true");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);

  // `diet=jain` (UI) → `jain=true` (API: only verified rows).
  const apiFilters = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v).map(([k, v]) => (k === "diet" ? [v, "true"] : [k, v])),
  );
  const params = { q, active, page, page_size: PAGE_SIZE, ...apiFilters };
  const list = useQuery({
    queryKey: ["inventory", resource, "list", params],
    queryFn: () => inventoryApi.list(resource, params),
    placeholderData: keepPreviousData,
  });
  const filtered = Boolean(q || Object.values(filters).some(Boolean));
  const Icon = config.icon;

  const addButton = isAdmin && (
    <Button onClick={() => setCreating(true)}>
      <Plus aria-hidden /> New {config.singular.toLowerCase()}
    </Button>
  );

  return (
    <>
      <PageHeader title={config.title} description={config.description} actions={addButton} />
      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder={config.searchPlaceholder} label={`Search ${config.title.toLowerCase()}`} />
          <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
            {config.filters.map((f) => (
              <FilterSelect key={f.param} filter={f} value={filters[f.param] ?? ""} onChange={(v) => { setFilters((s) => ({ ...s, [f.param]: v })); setPage(1); }} />
            ))}
            <NativeSelect aria-label="Filter by status" value={active} onChange={(e) => { setActive(e.target.value); setPage(1); }} className="sm:w-32">
              <option value="true">Active</option>
              <option value="false">Inactive</option>
              <option value="">All</option>
            </NativeSelect>
          </div>
        </div>

        {list.isPending ? (
          <TableSkeleton />
        ) : list.isError ? (
          <ErrorState message={list.error.message} onRetry={() => list.refetch()} />
        ) : list.data.items.length === 0 ? (
          <EmptyState
            icon={Icon}
            title={filtered ? `No ${config.title.toLowerCase()} match your filters` : `No ${config.title.toLowerCase()} yet`}
            description={filtered ? "Try a different search or clear the filters." : isAdmin ? undefined : "An administrator can add them."}
            action={!filtered && addButton}
          />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{config.singular}</TableHead>
                  {config.columns.map((c) => <TableHead key={c.header} className={c.className}>{c.header}</TableHead>)}
                  <TableHead className="hidden sm:table-cell">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((item) => (
                  <TableRow key={item.id} className="cursor-pointer" onClick={() => router.push(`${config.basePath}/${item.id}`)}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        {config.hasImages && <Thumb item={item} icon={Icon} />}
                        <div className="min-w-0">
                          <Link href={`${config.basePath}/${item.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                            {item.name}
                          </Link>
                          {item.is_demo && <DemoBadge className="ml-2 align-middle" />}
                          {config.subtitle && <div className="truncate text-xs text-muted-foreground sm:hidden">{config.subtitle(item)}</div>}
                        </div>
                      </div>
                    </TableCell>
                    {config.columns.map((c) => <TableCell key={c.header} className={c.className}>{c.render(item)}</TableCell>)}
                    <TableCell className="hidden sm:table-cell"><ActiveBadge status={item.is_active} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />
          </>
        )}
      </Card>
      {isAdmin && (
        <InventoryFormDialog config={config} open={creating} onOpenChange={setCreating} onSaved={(i) => router.push(`${config.basePath}/${i.id}`)} />
      )}
    </>
  );
}
