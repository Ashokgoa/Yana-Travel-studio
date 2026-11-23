// Mirrors backend/app/schemas/media.py

export type MediaEntityType = "country" | "city" | "attraction" | "hotel" | "restaurant" | "vehicle";
export type MediaCategory = MediaEntityType | "brand" | "library";
export type MediaSource = "upload" | "supplier" | "stock" | "ai_generated";

export type Media = {
  id: number;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  width: number;
  height: number;
  category: MediaCategory;
  source: MediaSource;
  description: string | null;
  alt_text: string | null;
  is_ai_generated: boolean;
  is_illustrative: boolean;
  created_at: string;
  usage_count: number;
  url: string;
  thumbnail_url: string;
};

export type MediaUsage = { link_id: number; entity_type: MediaEntityType; entity_id: number; entity_name: string | null; is_primary: boolean };
export type MediaDetail = Media & { usages: MediaUsage[] };

export type GalleryItem = { id: number; media_id: number; is_primary: boolean; sort_order: number; caption: string | null; media: Media };

export type UploadResult = { media: Media; created: boolean; link_id: number | null };
