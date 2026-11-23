"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, RefreshCw, Star, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { controlClass, FormField, NativeSelect } from "@/components/common/form-controls";
import { ErrorState } from "@/components/common/states";
import { formatDateTime } from "@/lib/format";
import { ApiError } from "@/services/api";
import { ACCEPT_ATTR, mediaApi, precheckFile } from "@/services/media";
import type { MediaDetail, MediaEntityType, MediaSource } from "@/types/media";

export const ENTITY_PATH: Record<MediaEntityType, string> = {
  country: "/inventory/countries",
  city: "/inventory/cities",
  attraction: "/inventory/sightseeing",
  hotel: "/inventory/hotels",
  restaurant: "/inventory/restaurants",
  vehicle: "/inventory/transportation",
};

const SOURCES: [MediaSource, string][] = [
  ["upload", "Own upload"],
  ["supplier", "Supplier / authorised"],
  ["stock", "Licensed stock"],
  ["ai_generated", "AI generated"],
];

export function IllustrativeBadge() {
  return (
    <span className="rounded-full bg-amber-100 px-2 py-0.5 font-sans text-[11px] font-semibold text-amber-800" title="Illustrative image, not a photo of the actual place">
      Illustrative
    </span>
  );
}

function MetadataForm({ media, canEdit }: { media: MediaDetail; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const [v, setV] = useState({
    description: media.description ?? "",
    alt_text: media.alt_text ?? "",
    source: media.source,
    is_illustrative: media.is_illustrative,
  });
  const save = useMutation({
    mutationFn: () => mediaApi.update(media.id, { ...v, description: v.description || null, alt_text: v.alt_text || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media"] });
      toast.success("Image details saved");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save"),
  });
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <FormField label="Description" htmlFor="md-desc" hint="Shown in the library and used as a caption suggestion.">
        <textarea id="md-desc" rows={2} disabled={!canEdit} className={`${controlClass} h-auto py-2`} value={v.description} onChange={(e) => setV({ ...v, description: e.target.value })} />
      </FormField>
      <FormField label="Alternative text" htmlFor="md-alt" hint="Short description for screen readers and PDFs.">
        <input id="md-alt" disabled={!canEdit} className={controlClass} value={v.alt_text} onChange={(e) => setV({ ...v, alt_text: e.target.value })} />
      </FormField>
      <FormField label="Source" htmlFor="md-src">
        <NativeSelect id="md-src" disabled={!canEdit} value={v.source} onChange={(e) => setV({ ...v, source: e.target.value as MediaSource })}>
          {SOURCES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </NativeSelect>
      </FormField>
      <label className="flex items-start gap-2.5 text-sm">
        <input
          type="checkbox"
          className="mt-0.5 size-4 accent-[var(--brand-teal)]"
          disabled={!canEdit || media.is_ai_generated}
          checked={v.is_illustrative || media.is_ai_generated}
          onChange={(e) => setV({ ...v, is_illustrative: e.target.checked })}
        />
        <span>
          Illustrative image, not a photo of the actual property or place.
          {media.is_ai_generated && <span className="block text-xs text-muted-foreground">AI-generated images are always illustrative.</span>}
        </span>
      </label>
      {canEdit && (
        <Button type="submit" disabled={save.isPending}>
          {save.isPending && <Loader2 className="animate-spin" aria-hidden />} Save details
        </Button>
      )}
    </form>
  );
}

export function MediaDetailDialog({ mediaId, onOpenChange, canEdit }: { mediaId: number | null; onOpenChange: (open: boolean) => void; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const replaceInput = useRef<HTMLInputElement>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const query = useQuery({ queryKey: ["media", "detail", mediaId], queryFn: () => mediaApi.get(mediaId!), enabled: mediaId !== null });

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ["media"] });
    queryClient.invalidateQueries({ queryKey: ["inventory"] });
  };
  const replace = useMutation({
    mutationFn: (file: File) => mediaApi.replace(mediaId!, file),
    onSuccess: () => { refreshAll(); toast.success("Image replaced everywhere it is used"); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not replace the image"),
  });
  const remove = useMutation({
    mutationFn: () => mediaApi.remove(mediaId!),
    onSuccess: () => { refreshAll(); toast.success("Image deleted"); setConfirmDelete(false); onOpenChange(false); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not delete the image"),
  });

  const m = query.data;
  return (
    <>
      <Dialog open={mediaId !== null} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Image details</DialogTitle>
            <DialogDescription>{m ? `${m.original_filename} · ${m.width}×${m.height} px · ${(m.size_bytes / 1024).toFixed(0)} KB` : "Loading…"}</DialogDescription>
          </DialogHeader>
          {query.isError ? (
            <ErrorState message={query.error.message} />
          ) : !m ? (
            <div className="h-64 animate-pulse rounded-xl bg-muted" />
          ) : (
            <div className="grid gap-6 md:grid-cols-[1.2fr_1fr]">
              <div className="space-y-3">
                {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                <img src={m.url} alt={m.alt_text ?? m.description ?? ""} className="w-full rounded-xl bg-muted object-contain" />
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  {m.is_illustrative && <IllustrativeBadge />}
                  Uploaded {formatDateTime(m.created_at)}
                </div>
                <div>
                  <p className="mb-1.5 text-sm font-medium">Used in {m.usages.length} place{m.usages.length === 1 ? "" : "s"}</p>
                  {m.usages.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Not attached to any record yet.</p>
                  ) : (
                    <ul className="space-y-1 text-sm">
                      {m.usages.map((u) => (
                        <li key={u.link_id} className="flex items-center gap-1.5">
                          {u.is_primary && <Star className="size-3.5 fill-brand-gold text-brand-gold" aria-label="Primary image" />}
                          <Link href={`${ENTITY_PATH[u.entity_type]}/${u.entity_id}`} className="text-brand-teal hover:underline" onClick={() => onOpenChange(false)}>
                            {u.entity_name ?? `${u.entity_type} #${u.entity_id}`}
                          </Link>
                          <span className="text-xs text-muted-foreground">({u.entity_type})</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              <div className="space-y-6">
                <MetadataForm key={m.id + m.url} media={m} canEdit={canEdit} />
                {canEdit && (
                  <div className="flex flex-wrap gap-2 border-t pt-4">
                    <Button variant="outline" onClick={() => replaceInput.current?.click()} disabled={replace.isPending}>
                      {replace.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <RefreshCw aria-hidden />} Replace file
                    </Button>
                    <Button variant="outline" className="text-destructive" onClick={() => setConfirmDelete(true)}>
                      <Trash2 aria-hidden /> Delete
                    </Button>
                    <input
                      ref={replaceInput}
                      type="file"
                      accept={ACCEPT_ATTR}
                      className="sr-only"
                      tabIndex={-1}
                      aria-hidden
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        e.target.value = "";
                        if (!f) return;
                        const problem = precheckFile(f);
                        if (problem) toast.error(problem);
                        else replace.mutate(f);
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this image everywhere?"
        description={m && m.usages.length
          ? `It is used in ${m.usages.length} place${m.usages.length === 1 ? "" : "s"} and will be removed from all of them. This cannot be undone.`
          : "The file will be permanently deleted. This cannot be undone."}
        confirmLabel="Delete image"
        destructive
        pending={remove.isPending}
        onConfirm={() => remove.mutate()}
      />
    </>
  );
}
