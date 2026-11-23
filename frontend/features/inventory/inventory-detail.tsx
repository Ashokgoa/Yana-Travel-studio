"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ExternalLink, Pencil, Power } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PageHeader } from "@/components/common/page-header";
import { DetailItem, ErrorState, TableSkeleton } from "@/components/common/states";
import { ActiveBadge } from "@/components/common/status-badge";
import { useAuth } from "@/features/auth/auth-provider";
import { DemoBadge, TriState } from "@/features/inventory/badges";
import { HotelRooms } from "@/features/inventory/hotel-rooms";
import { ImageGallery } from "@/features/media/image-gallery";
import { InventoryFormDialog } from "@/features/inventory/inventory-form-dialog";
import { Thumb } from "@/features/inventory/inventory-list";
import { humanize, RESOURCES, stars, type FieldDef } from "@/features/inventory/resource-config";
import { formatDateTime, formatMoney } from "@/lib/format";
import { handleFormError } from "@/lib/form-errors";
import { inventoryApi } from "@/services/inventory";
import type { Hotel, InventoryItem, ResourceKey } from "@/types/inventory";
import type { MediaEntityType } from "@/types/media";

const ENTITY_TYPE: Partial<Record<ResourceKey, MediaEntityType>> = {
  countries: "country",
  cities: "city",
  attractions: "attraction",
  hotels: "hotel",
  restaurants: "restaurant",
  vehicles: "vehicle",
};

const REF_OBJECT: Record<string, string> = {
  country_id: "country",
  city_id: "city",
  supplier_id: "supplier",
  category_id: "category",
};

function displayValue(field: FieldDef, item: InventoryItem): React.ReactNode {
  const v = item[field.name];
  switch (field.type) {
    case "tristate":
      return <TriState value={v} />;
    case "bool":
      return v ? "Yes" : "No";
    case "multi":
      return Array.isArray(v) && v.length ? (
        <span className="flex flex-wrap gap-1.5">
          {v.map((x) => <span key={String(x)} className="rounded-full bg-accent px-2.5 py-0.5 text-xs text-accent-foreground">{humanize(String(x))}</span>)}
        </span>
      ) : null;
    case "multiref": {
      const list = (item.operating_countries as { id: number; name: string }[] | undefined) ?? [];
      return list.length ? list.map((c) => c.name).join(", ") : null;
    }
    case "reference": {
      const ref = item[REF_OBJECT[field.name] ?? ""] as { name: string; country?: { name: string } } | null | undefined;
      return ref ? (ref.country ? `${ref.name}, ${ref.country.name}` : ref.name) : null;
    }
    case "decimal": {
      if (v === null || v === undefined || v === "") return null;
      const verified = item.price_is_verified === true;
      return (
        <span>
          {formatMoney(String(v), String(item.currency ?? "EUR"))}{" "}
          <span className={verified ? "text-xs text-emerald-700" : "text-xs text-amber-700"}>{verified ? "verified" : "estimated"}</span>
        </span>
      );
    }
    case "select":
      if (v === null || v === undefined || v === "") return null;
      return field.name === "star_rating" ? <span className="text-brand-gold">{stars(v)}</span> : humanize(String(v));
    case "int":
      return v === null || v === undefined ? null : String(v);
    default:
      return v === null || v === undefined || v === "" ? null : <span className="whitespace-pre-line">{String(v)}</span>;
  }
}

export function InventoryDetail({ resource, id }: { resource: ResourceKey; id: number }) {
  const config = RESOURCES[resource];
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const isAdmin = hasRole("admin");
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);

  const query = useQuery({ queryKey: ["inventory", resource, "detail", id], queryFn: () => inventoryApi.get(resource, id) });
  const toggle = useMutation({
    mutationFn: () => inventoryApi.setActive(resource, id, !query.data?.is_active),
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      toast.success(`${config.singular} ${item.is_active ? "reactivated" : "deactivated"}`);
      setConfirm(false);
    },
    onError: (e) => handleFormError(e),
  });

  if (query.isPending) return <TableSkeleton rows={6} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const item = query.data;
  const sections = [...new Set(config.fields.map((f) => f.section))].filter((s) => s !== "Status" && s !== "Location");
  const lat = item.latitude as number | null | undefined;
  const lng = item.longitude as number | null | undefined;

  return (
    <>
      <PageHeader
        back={{ href: config.basePath, label: config.title }}
        title={
          <span className="flex flex-wrap items-center gap-3">
            {config.hasImages && <Thumb item={item} icon={config.icon} size="size-12" />}
            {item.name}
            <ActiveBadge status={item.is_active} />
            {item.is_demo && <DemoBadge />}
          </span>
        }
        description={config.subtitle?.(item)}
        actions={
          isAdmin && (
            <>
              <Button variant="outline" onClick={() => setConfirm(true)}>
                <Power aria-hidden /> {item.is_active ? "Deactivate" : "Reactivate"}
              </Button>
              <Button onClick={() => setEditing(true)}>
                <Pencil aria-hidden /> Edit
              </Button>
            </>
          )
        }
      />

      {item.is_demo && (
        <p className="mb-6 rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-800">
          This is <strong>demonstration data</strong>: names, prices and availability are fictional. Replace it with verified supplier information before using it in proposals.
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {sections.map((section) => (
            <Card key={section}>
              <CardHeader>
                <CardTitle>{section}</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid gap-5 sm:grid-cols-2">
                  {config.fields.filter((f) => f.section === section && f.name !== "name").map((f) => (
                    <div key={f.name} className={f.wide || f.type === "textarea" || f.type === "multi" || f.type === "multiref" ? "sm:col-span-2" : undefined}>
                      <DetailItem label={f.label}>{displayValue(f, item)}</DetailItem>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          ))}
          {resource === "hotels" && <HotelRooms hotel={item as Hotel} canEdit={isAdmin} />}
        </div>

        <div className="space-y-6">
          {config.hasImages && ENTITY_TYPE[resource] && (
            <ImageGallery entityType={ENTITY_TYPE[resource]!} entityId={item.id} canEdit={isAdmin} />
          )}
          <Card>
            <CardHeader>
              <CardTitle>Record</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-5">
                {config.fields.some((f) => f.name === "address") && <DetailItem label="Address">{(item.address as string) || null}</DetailItem>}
                {config.fields.some((f) => f.name === "latitude") && (
                  <DetailItem label="Location">
                    {lat != null && lng != null ? (
                      <a
                        className="inline-flex items-center gap-1 text-brand-teal hover:underline"
                        href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=14/${lat}/${lng}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {lat.toFixed(4)}, {lng.toFixed(4)} <ExternalLink className="size-3" aria-hidden />
                      </a>
                    ) : null}
                  </DetailItem>
                )}
                <DetailItem label="Last updated">{formatDateTime(item.updated_at)}</DetailItem>
                <DetailItem label="Created">{formatDateTime(item.created_at)}</DetailItem>
              </dl>
            </CardContent>
          </Card>
        </div>
      </div>

      {isAdmin && (
        <>
          <InventoryFormDialog config={config} open={editing} onOpenChange={setEditing} item={item} />
          <ConfirmDialog
            open={confirm}
            onOpenChange={setConfirm}
            title={`${item.is_active ? "Deactivate" : "Reactivate"} ${item.name}?`}
            description={
              item.is_active
                ? "Inactive records stay on file but won't be offered for new itineraries."
                : "The record will be available again for new itineraries."
            }
            confirmLabel={item.is_active ? "Deactivate" : "Reactivate"}
            destructive={item.is_active}
            pending={toggle.isPending}
            onConfirm={() => toggle.mutate()}
          />
        </>
      )}
    </>
  );
}
