import { api, type QueryParams } from "@/services/api";
import type { Page } from "@/types/crm";
import type { GalleryItem, Media, MediaDetail, MediaEntityType, MediaSource, UploadResult } from "@/types/media";

export const MAX_UPLOAD_MB = 10;
export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const ACCEPT_ATTR = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";

/** Quick client-side check so obviously wrong files fail fast; the server re-validates everything. */
export function precheckFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type) && !/\.(jpe?g|png|webp)$/i.test(file.name)) {
    return `${file.name}: only JPG, PNG or WEBP images are allowed.`;
  }
  if (file.size > MAX_UPLOAD_MB * 1_048_576) {
    return `${file.name}: ${(file.size / 1_048_576).toFixed(1)} MB is larger than the ${MAX_UPLOAD_MB} MB limit.`;
  }
  return null;
}

export const mediaApi = {
  list: (params?: QueryParams) => api.get<Page<Media>>("/media", params),
  get: (id: number) => api.get<MediaDetail>(`/media/${id}`),
  upload: (
    file: File,
    opts: { entityType?: MediaEntityType; entityId?: number; category?: string; description?: string; source?: MediaSource; isIllustrative?: boolean } = {},
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (opts.entityType && opts.entityId) {
      form.append("entity_type", opts.entityType);
      form.append("entity_id", String(opts.entityId));
    }
    if (opts.category) form.append("category", opts.category);
    if (opts.description) form.append("description", opts.description);
    if (opts.source) form.append("source", opts.source);
    if (opts.isIllustrative) form.append("is_illustrative", "true");
    return api.upload<UploadResult>("/media/upload", form);
  },
  update: (id: number, body: Partial<Pick<Media, "description" | "alt_text" | "source" | "is_illustrative">>) =>
    api.patch<Media>(`/media/${id}`, body),
  replace: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.upload<Media>(`/media/${id}/replace`, form);
  },
  remove: (id: number) => api.delete<void>(`/media/${id}`),

  gallery: (entityType: MediaEntityType, entityId: number) => api.get<GalleryItem[]>(`/media/gallery/${entityType}/${entityId}`),
  link: (entityType: MediaEntityType, entityId: number, mediaId: number) =>
    api.post<GalleryItem[]>("/media/links", { entity_type: entityType, entity_id: entityId, media_id: mediaId }),
  unlink: (linkId: number) => api.delete<GalleryItem[]>(`/media/links/${linkId}`),
  setPrimary: (linkId: number) => api.post<GalleryItem[]>(`/media/links/${linkId}/primary`),
  caption: (linkId: number, caption: string | null) => api.put<GalleryItem[]>(`/media/links/${linkId}/caption`, { caption }),
  reorder: (entityType: MediaEntityType, entityId: number, linkIds: number[]) =>
    api.put<GalleryItem[]>(`/media/gallery/${entityType}/${entityId}/order`, { link_ids: linkIds }),
};
