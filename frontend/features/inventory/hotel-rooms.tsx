"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { BedDouble, CalendarRange, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { controlClass, FormField, NativeSelect } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { CURRENCIES } from "@/features/inventory/resource-config";
import { formatDate, formatMoney } from "@/lib/format";
import { ApiError } from "@/services/api";
import { inventoryApi } from "@/services/inventory";
import type { Hotel, RoomType, SeasonalRate } from "@/types/inventory";

const Est = ({ verified }: { verified: boolean }) => (
  <span className={verified ? "ml-1 text-[11px] text-emerald-700" : "ml-1 text-[11px] text-amber-700"}>{verified ? "verified" : "est."}</span>
);

type Editing<T> = { kind: "new" } | { kind: "edit"; row: T } | null;

/** Remount key so each opened dialog starts from fresh values. */
const editKey = (e: Editing<{ id: number }>) => (e === null ? "closed" : e.kind === "new" ? "new" : `edit-${e.row.id}`);

function useHotelMutation(hotelId: number, onDone: () => void, setErrors: (e: Record<string, string>) => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fn: () => Promise<Hotel>) => fn(),
    onSuccess: (hotel) => {
      queryClient.setQueryData(["inventory", "hotels", "detail", hotelId], hotel);
      queryClient.invalidateQueries({ queryKey: ["inventory", "hotels", "list"] });
      onDone();
    },
    onError: (e) => {
      if (e instanceof ApiError && e.body?.details?.length) {
        const errs: Record<string, string> = {};
        for (const d of e.body.details) errs[d.field || "_"] = d.message;
        setErrors(errs);
        if (errs._) toast.error(errs._);
      } else toast.error(e instanceof ApiError ? e.message : "Could not save.");
    },
  });
}

function RoomTypeDialog({ hotel, editing, onClose }: { hotel: Hotel; editing: Editing<RoomType>; onClose: () => void }) {
  const row = editing?.kind === "edit" ? editing.row : undefined;
  // Initial values come from props; the parent remounts this dialog (via `key`) on each open.
  const [v, setV] = useState(() =>
    row
      ? { name: row.name, max_occupancy: String(row.max_occupancy), bed_config: row.bed_config ?? "", base_price: row.base_price ?? "", currency: row.currency, price_is_verified: row.price_is_verified }
      : { name: "", max_occupancy: "2", bed_config: "", base_price: "", currency: "EUR", price_is_verified: false },
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const m = useHotelMutation(hotel.id, () => { toast.success(row ? "Room type updated" : "Room type added"); onClose(); }, setErrors);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!v.name.trim()) return setErrors({ name: "Room type name is required" });
    const body = { ...v, max_occupancy: Number(v.max_occupancy) || 1, bed_config: v.bed_config || null, base_price: v.base_price.replace(",", ".") || null };
    m.mutate(() => (row ? inventoryApi.updateRoomType(hotel.id, row.id, body) : inventoryApi.addRoomType(hotel.id, body)));
  };

  return (
    <FormDialog open={!!editing} onOpenChange={(o) => !o && onClose()} title={row ? "Edit room type" : "Add room type"} formId="room-type-form" pending={m.isPending}>
      <form id="room-type-form" noValidate onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <FormField label="Room type" htmlFor="rt-name" required error={errors.name} className="sm:col-span-2">
          <input id="rt-name" className={controlClass} placeholder="e.g. Superior Double" value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} autoFocus />
        </FormField>
        <FormField label="Max occupancy" htmlFor="rt-occ" error={errors.max_occupancy}>
          <input id="rt-occ" inputMode="numeric" className={controlClass} value={v.max_occupancy} onChange={(e) => setV({ ...v, max_occupancy: e.target.value })} />
        </FormField>
        <FormField label="Beds" htmlFor="rt-bed" error={errors.bed_config}>
          <input id="rt-bed" className={controlClass} placeholder="e.g. 1 king or 2 singles" value={v.bed_config} onChange={(e) => setV({ ...v, bed_config: e.target.value })} />
        </FormField>
        <FormField label="Base price (per room / night)" htmlFor="rt-price" error={errors.base_price}>
          <input id="rt-price" inputMode="decimal" className={controlClass} value={v.base_price} onChange={(e) => setV({ ...v, base_price: e.target.value })} />
        </FormField>
        <FormField label="Currency" htmlFor="rt-cur">
          <NativeSelect id="rt-cur" value={v.currency} onChange={(e) => setV({ ...v, currency: e.target.value })}>
            {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
          </NativeSelect>
        </FormField>
        <label className="flex items-center gap-2.5 text-sm sm:col-span-2">
          <input type="checkbox" className="size-4 accent-[var(--brand-teal)]" checked={v.price_is_verified} onChange={(e) => setV({ ...v, price_is_verified: e.target.checked })} />
          Price verified with the supplier (otherwise shown as estimated)
        </label>
      </form>
    </FormDialog>
  );
}

function RateDialog({ hotel, editing, onClose }: { hotel: Hotel; editing: Editing<SeasonalRate>; onClose: () => void }) {
  const row = editing?.kind === "edit" ? editing.row : undefined;
  // Initial values come from props; the parent remounts this dialog (via `key`) on each open.
  const [v, setV] = useState(() =>
    row
      ? { room_type_id: String(row.room_type_id), season_name: row.season_name, valid_from: row.valid_from, valid_to: row.valid_to, price: row.price, currency: row.currency, is_verified: row.is_verified }
      : { room_type_id: String(hotel.room_types[0]?.id ?? ""), season_name: "", valid_from: "", valid_to: "", price: "", currency: "EUR", is_verified: false },
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const m = useHotelMutation(hotel.id, () => { toast.success(row ? "Rate updated" : "Rate added"); onClose(); }, setErrors);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const missing: Record<string, string> = {};
    if (!v.season_name.trim()) missing.season_name = "Season name is required";
    if (!v.valid_from) missing.valid_from = "Required";
    if (!v.valid_to) missing.valid_to = "Required";
    if (!v.price) missing.price = "Required";
    if (Object.keys(missing).length) return setErrors(missing);
    const body = { ...v, room_type_id: Number(v.room_type_id), price: v.price.replace(",", ".") };
    m.mutate(() => (row ? inventoryApi.updateRate(hotel.id, row.id, body) : inventoryApi.addRate(hotel.id, body)));
  };

  return (
    <FormDialog open={!!editing} onOpenChange={(o) => !o && onClose()} title={row ? "Edit seasonal rate" : "Add seasonal rate"} formId="rate-form" pending={m.isPending}>
      <form id="rate-form" noValidate onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <FormField label="Room type" htmlFor="rate-rt" required className="sm:col-span-2">
          <NativeSelect id="rate-rt" value={v.room_type_id} onChange={(e) => setV({ ...v, room_type_id: e.target.value })}>
            {hotel.room_types.map((rt) => <option key={rt.id} value={rt.id}>{rt.name}</option>)}
          </NativeSelect>
        </FormField>
        <FormField label="Season" htmlFor="rate-season" required error={errors.season_name} className="sm:col-span-2">
          <input id="rate-season" className={controlClass} placeholder="e.g. Summer 2027" value={v.season_name} onChange={(e) => setV({ ...v, season_name: e.target.value })} autoFocus />
        </FormField>
        <FormField label="Valid from" htmlFor="rate-from" required error={errors.valid_from}>
          <input id="rate-from" type="date" className={controlClass} value={v.valid_from} onChange={(e) => setV({ ...v, valid_from: e.target.value })} />
        </FormField>
        <FormField label="Valid to" htmlFor="rate-to" required error={errors.valid_to || errors._}>
          <input id="rate-to" type="date" min={v.valid_from || undefined} className={controlClass} value={v.valid_to} onChange={(e) => setV({ ...v, valid_to: e.target.value })} />
        </FormField>
        <FormField label="Price (per room / night)" htmlFor="rate-price" required error={errors.price}>
          <input id="rate-price" inputMode="decimal" className={controlClass} value={v.price} onChange={(e) => setV({ ...v, price: e.target.value })} />
        </FormField>
        <FormField label="Currency" htmlFor="rate-cur">
          <NativeSelect id="rate-cur" value={v.currency} onChange={(e) => setV({ ...v, currency: e.target.value })}>
            {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
          </NativeSelect>
        </FormField>
        <label className="flex items-center gap-2.5 text-sm sm:col-span-2">
          <input type="checkbox" className="size-4 accent-[var(--brand-teal)]" checked={v.is_verified} onChange={(e) => setV({ ...v, is_verified: e.target.checked })} />
          Verified against a supplier quotation
        </label>
      </form>
    </FormDialog>
  );
}

export function HotelRooms({ hotel, canEdit }: { hotel: Hotel; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const [roomEditing, setRoomEditing] = useState<Editing<RoomType>>(null);
  const [rateEditing, setRateEditing] = useState<Editing<SeasonalRate>>(null);
  const [deleting, setDeleting] = useState<{ kind: "room" | "rate"; id: number; label: string } | null>(null);
  const roomName = (id: number) => hotel.room_types.find((r) => r.id === id)?.name ?? "—";

  const del = useMutation({
    mutationFn: () =>
      deleting!.kind === "room" ? inventoryApi.deleteRoomType(hotel.id, deleting!.id) : inventoryApi.deleteRate(hotel.id, deleting!.id),
    onSuccess: (h) => {
      queryClient.setQueryData(["inventory", "hotels", "detail", hotel.id], h);
      queryClient.invalidateQueries({ queryKey: ["inventory", "hotels", "list"] });
      toast.success("Deleted");
      setDeleting(null);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not delete."),
  });

  const actions = (onEdit: () => void, onDelete: () => void, label: string) =>
    canEdit && (
      <div className="flex justify-end gap-1">
        <Button variant="ghost" size="icon" aria-label={`Edit ${label}`} onClick={onEdit}><Pencil /></Button>
        <Button variant="ghost" size="icon" aria-label={`Delete ${label}`} onClick={onDelete}><Trash2 /></Button>
      </div>
    );

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Room types</CardTitle>
          {canEdit && <Button size="sm" variant="outline" onClick={() => setRoomEditing({ kind: "new" })}><Plus aria-hidden /> Add room type</Button>}
        </CardHeader>
        <CardContent>
          {hotel.room_types.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground"><BedDouble className="size-4" aria-hidden /> No room types yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Room type</TableHead>
                  <TableHead className="text-right">Sleeps</TableHead>
                  <TableHead className="hidden sm:table-cell">Beds</TableHead>
                  <TableHead>Base price / night</TableHead>
                  {canEdit && <TableHead className="w-24"><span className="sr-only">Actions</span></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {hotel.room_types.map((rt) => (
                  <TableRow key={rt.id}>
                    <TableCell className="font-medium">{rt.name}</TableCell>
                    <TableCell className="text-right tabular-nums">{rt.max_occupancy}</TableCell>
                    <TableCell className="hidden sm:table-cell">{rt.bed_config ?? "—"}</TableCell>
                    <TableCell>{rt.base_price ? <>{formatMoney(rt.base_price, rt.currency)}<Est verified={rt.price_is_verified} /></> : "—"}</TableCell>
                    {canEdit && <TableCell>{actions(() => setRoomEditing({ kind: "edit", row: rt }), () => setDeleting({ kind: "room", id: rt.id, label: rt.name }), rt.name)}</TableCell>}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Seasonal rates</CardTitle>
          {canEdit && (
            <Button size="sm" variant="outline" disabled={hotel.room_types.length === 0} title={hotel.room_types.length === 0 ? "Add a room type first" : undefined} onClick={() => setRateEditing({ kind: "new" })}>
              <Plus aria-hidden /> Add rate
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {hotel.rates.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground"><CalendarRange className="size-4" aria-hidden /> No seasonal rates. The room type&apos;s base price is used as an estimate.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Season</TableHead>
                  <TableHead>Room type</TableHead>
                  <TableHead className="hidden sm:table-cell">Valid</TableHead>
                  <TableHead>Price / night</TableHead>
                  {canEdit && <TableHead className="w-24"><span className="sr-only">Actions</span></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {hotel.rates.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">{r.season_name}</TableCell>
                    <TableCell>{roomName(r.room_type_id)}</TableCell>
                    <TableCell className="hidden sm:table-cell whitespace-nowrap">{formatDate(r.valid_from)} – {formatDate(r.valid_to)}</TableCell>
                    <TableCell>{formatMoney(r.price, r.currency)}<Est verified={r.is_verified} /></TableCell>
                    {canEdit && <TableCell>{actions(() => setRateEditing({ kind: "edit", row: r }), () => setDeleting({ kind: "rate", id: r.id, label: r.season_name }), r.season_name)}</TableCell>}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <RoomTypeDialog key={editKey(roomEditing)} hotel={hotel} editing={roomEditing} onClose={() => setRoomEditing(null)} />
      <RateDialog key={editKey(rateEditing)} hotel={hotel} editing={rateEditing} onClose={() => setRateEditing(null)} />
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={`Delete ${deleting?.label}?`}
        description={deleting?.kind === "room" ? "This also deletes its seasonal rates. This cannot be undone." : "This cannot be undone."}
        confirmLabel="Delete"
        destructive
        pending={del.isPending}
        onConfirm={() => del.mutate()}
      />
    </>
  );
}
