"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, ImageIcon, Images, MessageSquareText, Star, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { controlClass, FormField } from "@/components/common/form-controls";
import { FormDialog } from "@/components/common/form-dialog";
import { ErrorState } from "@/components/common/states";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { mediaApi } from "@/services/media";
import type { GalleryItem, MediaEntityType } from "@/types/media";
import { IllustrativeBadge, MediaDetailDialog } from "@/features/media/media-detail-dialog";
import { MediaPickerDialog } from "@/features/media/media-picker-dialog";
import { UploadZone } from "@/features/media/upload-zone";

const iconBtn =
  "flex size-8 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur transition hover:bg-black/75 " +
  "focus-visible:ring-2 focus-visible:ring-white focus-visible:outline-none disabled:opacity-40";

export function ImageGallery({ entityType, entityId, canEdit }: { entityType: MediaEntityType; entityId: number; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const key = ["media", "gallery", entityType, entityId];
  const gallery = useQuery({ queryKey: key, queryFn: () => mediaApi.gallery(entityType, entityId) });
  const [picking, setPicking] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [removing, setRemoving] = useState<GalleryItem | null>(null);
  const [captioning, setCaptioning] = useState<GalleryItem | null>(null);
  const [caption, setCaption] = useState("");
  const [dragId, setDragId] = useState<number | null>(null);

  const apply = (items: GalleryItem[]) => {
    queryClient.setQueryData(key, items);
    queryClient.invalidateQueries({ queryKey: ["inventory"] }); // list thumbnails use the primary image
    queryClient.invalidateQueries({ queryKey: ["media", "list"] });
  };
  const onError = (e: unknown) => toast.error(e instanceof ApiError ? e.message : "Something went wrong");
  const action = useMutation({ mutationFn: (fn: () => Promise<GalleryItem[]>) => fn(), onSuccess: apply, onError });
  const pick = useMutation({
    mutationFn: async (ids: number[]) => {
      let items: GalleryItem[] = gallery.data ?? [];
      for (const id of ids) items = await mediaApi.link(entityType, entityId, id);
      return items;
    },
    onSuccess: (items) => { apply(items); setPicking(false); toast.success("Images added"); },
    onError,
  });

  const items = gallery.data ?? [];
  const move = (index: number, delta: number) => {
    const ids = items.map((i) => i.id);
    const [moved] = ids.splice(index, 1);
    ids.splice(index + delta, 0, moved);
    action.mutate(() => mediaApi.reorder(entityType, entityId, ids));
  };
  const dropOn = (targetId: number) => {
    if (dragId === null || dragId === targetId) return;
    const ids = items.map((i) => i.id).filter((id) => id !== dragId);
    ids.splice(ids.indexOf(targetId), 0, dragId);
    setDragId(null);
    action.mutate(() => mediaApi.reorder(entityType, entityId, ids));
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Photos {items.length > 0 && <span className="font-sans text-sm font-normal text-muted-foreground">({items.length})</span>}</CardTitle>
        {canEdit && (
          <Button size="sm" variant="outline" onClick={() => setPicking(true)}>
            <Images aria-hidden /> From library
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {gallery.isError ? (
          <ErrorState message={gallery.error.message} onRetry={() => gallery.refetch()} />
        ) : gallery.isPending ? (
          <div className="aspect-[4/3] animate-pulse rounded-xl bg-muted" />
        ) : items.length === 0 ? (
          !canEdit && (
            <p className="flex flex-col items-center gap-2 py-6 text-center text-sm text-muted-foreground">
              <ImageIcon className="size-6" aria-hidden /> No photos yet.
            </p>
          )
        ) : (
          <ul className="grid grid-cols-2 gap-3" aria-label="Photos (first is shown first in proposals)">
            {items.map((item, index) => (
              <li
                key={item.id}
                draggable={canEdit}
                onDragStart={() => setDragId(item.id)}
                onDragOver={(e) => canEdit && e.preventDefault()}
                onDrop={() => dropOn(item.id)}
                className={cn("group relative overflow-hidden rounded-lg bg-muted", index === 0 && "col-span-2", dragId === item.id && "opacity-50")}
              >
                <button type="button" className="block w-full focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none" onClick={() => setDetailId(item.media_id)} aria-label={`Open image details${item.caption ? `: ${item.caption}` : ""}`}>
                  {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                  <img src={index === 0 ? item.media.url : item.media.thumbnail_url} alt={item.media.alt_text ?? item.caption ?? ""} className="aspect-[4/3] w-full object-cover" loading="lazy" />
                </button>
                <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-2">
                  <span className="flex flex-wrap gap-1">
                    {item.is_primary && (
                      <span className="flex items-center gap-1 rounded-full bg-brand-gold px-2 py-0.5 font-sans text-[11px] font-semibold text-primary">
                        <Star className="size-3 fill-current" aria-hidden /> Primary
                      </span>
                    )}
                    {item.media.is_illustrative && <IllustrativeBadge />}
                  </span>
                </div>
                {item.caption && <p className="absolute inset-x-0 bottom-0 truncate bg-gradient-to-t from-black/70 to-transparent px-2 pt-5 pb-1.5 text-xs text-white">{item.caption}</p>}
                {canEdit && (
                  <div className="absolute top-2 right-2 flex gap-1 opacity-100 transition sm:opacity-0 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100">
                    {!item.is_primary && (
                      <button type="button" className={iconBtn} title="Make primary" aria-label="Make primary image" onClick={() => action.mutate(() => mediaApi.setPrimary(item.id))}>
                        <Star className="size-4" />
                      </button>
                    )}
                    <button type="button" className={iconBtn} title="Move earlier" aria-label="Move earlier" disabled={index === 0} onClick={() => move(index, -1)}>
                      <ChevronLeft className="size-4" />
                    </button>
                    <button type="button" className={iconBtn} title="Move later" aria-label="Move later" disabled={index === items.length - 1} onClick={() => move(index, 1)}>
                      <ChevronRight className="size-4" />
                    </button>
                    <button type="button" className={iconBtn} title="Caption" aria-label="Edit caption" onClick={() => { setCaption(item.caption ?? ""); setCaptioning(item); }}>
                      <MessageSquareText className="size-4" />
                    </button>
                    <button type="button" className={iconBtn} title="Remove from this record" aria-label="Remove from this record" onClick={() => setRemoving(item)}>
                      <X className="size-4" />
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {canEdit && (
          <UploadZone
            compact={items.length > 0}
            onUpload={(file) => mediaApi.upload(file, { entityType, entityId })}
            onDone={() => { queryClient.invalidateQueries({ queryKey: key }); queryClient.invalidateQueries({ queryKey: ["inventory"] }); }}
          />
        )}
        {canEdit && items.length > 1 && <p className="text-xs text-muted-foreground">Drag photos or use the arrows to reorder. The primary photo is used in lists and proposals.</p>}
      </CardContent>

      <MediaPickerDialog open={picking} onOpenChange={setPicking} excludeIds={items.map((i) => i.media_id)} onPick={(ids) => pick.mutate(ids)} pending={pick.isPending} />
      <MediaDetailDialog mediaId={detailId} onOpenChange={(o) => !o && setDetailId(null)} canEdit={canEdit} />
      <ConfirmDialog
        open={!!removing}
        onOpenChange={(o) => !o && setRemoving(null)}
        title="Remove this photo from the record?"
        description="The image stays in the image library and in any other records that use it."
        confirmLabel="Remove"
        pending={action.isPending}
        onConfirm={() => { action.mutate(() => mediaApi.unlink(removing!.id)); setRemoving(null); }}
      />
      <FormDialog open={!!captioning} onOpenChange={(o) => !o && setCaptioning(null)} title="Photo caption" formId="caption-form" pending={action.isPending}>
        <form
          id="caption-form"
          onSubmit={(e) => {
            e.preventDefault();
            action.mutate(() => mediaApi.caption(captioning!.id, caption.trim() || null));
            setCaptioning(null);
          }}
        >
          <FormField label="Caption" htmlFor="caption-input" hint="Shown with this photo for this record (e.g. 'Deluxe room').">
            <input id="caption-input" maxLength={300} autoFocus className={controlClass} value={caption} onChange={(e) => setCaption(e.target.value)} />
          </FormField>
        </form>
      </FormDialog>
    </Card>
  );
}
