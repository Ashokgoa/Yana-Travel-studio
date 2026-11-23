"use client";

import { useState } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { Images } from "lucide-react";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/common/form-controls";
import { Pagination, SearchInput } from "@/components/common/list-controls";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState, ErrorState } from "@/components/common/states";
import { useAuth } from "@/features/auth/auth-provider";
import { IllustrativeBadge, MediaDetailDialog } from "@/features/media/media-detail-dialog";
import { UploadZone } from "@/features/media/upload-zone";
import { mediaApi } from "@/services/media";

export const CATEGORY_LABELS: Record<string, string> = {
  library: "General library",
  country: "Countries",
  city: "Cities",
  attraction: "Sightseeing",
  hotel: "Hotels",
  restaurant: "Restaurants",
  vehicle: "Transportation",
  brand: "Branding",
};

const PAGE_SIZE = 24;

export function MediaLibrary() {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [illustrative, setIllustrative] = useState("");
  const [page, setPage] = useState(1);
  const [detailId, setDetailId] = useState<number | null>(null);

  const params = { q, category, illustrative, page, page_size: PAGE_SIZE };
  const list = useQuery({ queryKey: ["media", "list", params], queryFn: () => mediaApi.list(params), placeholderData: keepPreviousData });

  return (
    <>
      <PageHeader
        title="Image Library"
        description="Every uploaded photo in one place. Reuse images across hotels, sightseeing, cities and proposals without duplicating files."
      />
      <div className="mb-6">
        <UploadZone
          label="Upload photos to the library"
          onUpload={(file) => mediaApi.upload(file, { category: "library" })}
          onDone={() => queryClient.invalidateQueries({ queryKey: ["media", "list"] })}
        />
      </div>
      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Search description or file name" label="Search images" />
          <div className="grid grid-cols-2 gap-3 sm:flex">
            <NativeSelect aria-label="Category" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }} className="sm:w-48">
              <option value="">All categories</option>
              {Object.entries(CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </NativeSelect>
            <NativeSelect aria-label="Image type" value={illustrative} onChange={(e) => { setIllustrative(e.target.value); setPage(1); }} className="sm:w-48">
              <option value="">Photos and illustrative</option>
              <option value="false">Real photos only</option>
              <option value="true">Illustrative only</option>
            </NativeSelect>
          </div>
        </div>
        {list.isError ? (
          <ErrorState message={list.error.message} onRetry={() => list.refetch()} />
        ) : !list.data ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="aspect-[4/3] animate-pulse rounded-lg bg-muted" />)}</div>
        ) : list.data.items.length === 0 ? (
          <EmptyState icon={Images} title={q || category || illustrative ? "No images match your filters" : "No images yet"} description="Upload photos above, or add them from any hotel, sightseeing or city page." />
        ) : (
          <>
            <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {list.data.items.map((m) => (
                <li key={m.id}>
                  <button type="button" onClick={() => setDetailId(m.id)} className="group block w-full overflow-hidden rounded-lg text-left ring-1 ring-border transition hover:ring-brand-teal focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none">
                    <span className="relative block">
                      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                      <img src={m.thumbnail_url} alt={m.alt_text ?? m.description ?? m.original_filename} className="aspect-[4/3] w-full bg-muted object-cover transition group-hover:scale-[1.02]" loading="lazy" />
                      {m.is_illustrative && <span className="absolute top-2 left-2"><IllustrativeBadge /></span>}
                    </span>
                    <span className="block px-3 py-2">
                      <span className="block truncate text-sm font-medium">{m.description ?? m.original_filename}</span>
                      <span className="block text-xs text-muted-foreground">
                        {CATEGORY_LABELS[m.category] ?? m.category} · used in {m.usage_count} place{m.usage_count === 1 ? "" : "s"}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPageChange={setPage} />
          </>
        )}
      </Card>
      <MediaDetailDialog mediaId={detailId} onOpenChange={(o) => !o && setDetailId(null)} canEdit={hasRole("admin")} />
    </>
  );
}
