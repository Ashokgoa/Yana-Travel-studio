"use client";

import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Check, Images, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { NativeSelect } from "@/components/common/form-controls";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { EmptyState, ErrorState } from "@/components/common/states";
import { cn } from "@/lib/utils";
import { mediaApi } from "@/services/media";
import { IllustrativeBadge } from "@/features/media/media-detail-dialog";
import { CATEGORY_LABELS } from "@/features/media/media-library";

const PAGE_SIZE = 24;

/** Choose existing library images (reuse without duplicating files). */
export function MediaPickerDialog({
  open,
  onOpenChange,
  excludeIds,
  onPick,
  pending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  excludeIds: number[];
  onPick: (mediaIds: number[]) => void;
  pending?: boolean;
}) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<number[]>([]);
  const params = { q, category, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["media", "list", params], queryFn: () => mediaApi.list(params), enabled: open, placeholderData: keepPreviousData });

  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) setSelected([]); onOpenChange(o); }}>
      <DialogContent className="max-h-[92vh] gap-0 overflow-hidden p-0 sm:max-w-4xl">
        <DialogHeader className="border-b px-6 pt-6 pb-4">
          <DialogTitle className="font-heading text-xl">Choose from image library</DialogTitle>
          <DialogDescription>Reuse photos already uploaded. The same file is shared, not copied.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[calc(92vh-11rem)] overflow-y-auto px-6 py-4">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row">
            <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Search description or file name" label="Search images" />
            <NativeSelect aria-label="Category" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }} className="sm:w-48">
              <option value="">All categories</option>
              {Object.entries(CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </NativeSelect>
          </div>
          {list.isError ? (
            <ErrorState message={list.error.message} onRetry={() => list.refetch()} />
          ) : !list.data ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="aspect-[4/3] animate-pulse rounded-lg bg-muted" />)}</div>
          ) : list.data.items.length === 0 ? (
            <EmptyState icon={Images} title="No images found" description="Upload photos first, then reuse them here." />
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {list.data.items.map((m) => {
                  const already = excludeIds.includes(m.id);
                  const on = selected.includes(m.id);
                  return (
                    <button
                      key={m.id}
                      type="button"
                      disabled={already}
                      aria-pressed={on}
                      onClick={() => toggle(m.id)}
                      className={cn(
                        "group relative overflow-hidden rounded-lg text-left ring-2 transition focus-visible:ring-ring focus-visible:outline-none",
                        on ? "ring-brand-teal" : "ring-transparent hover:ring-border",
                        already && "cursor-not-allowed opacity-40",
                      )}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                      <img src={m.thumbnail_url} alt={m.alt_text ?? m.description ?? m.original_filename} className="aspect-[4/3] w-full bg-muted object-cover" loading="lazy" />
                      {on && <span className="absolute top-2 right-2 flex size-6 items-center justify-center rounded-full bg-brand-teal text-white"><Check className="size-4" aria-hidden /></span>}
                      {m.is_illustrative && <span className="absolute top-2 left-2"><IllustrativeBadge /></span>}
                      <span className="block truncate px-1 py-1 text-xs text-muted-foreground">{already ? "Already in gallery" : m.description ?? m.original_filename}</span>
                    </button>
                  );
                })}
              </div>
              <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />
            </>
          )}
        </div>
        <DialogFooter className="m-0 border-t px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
          <Button disabled={!selected.length || pending} onClick={() => { onPick(selected); setSelected([]); }}>
            {pending && <Loader2 className="animate-spin" aria-hidden />}
            Add {selected.length || ""} image{selected.length === 1 ? "" : "s"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
