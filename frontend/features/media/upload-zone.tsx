"use client";

import { useRef, useState } from "react";
import { ImagePlus, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { ACCEPT_ATTR, MAX_UPLOAD_MB, precheckFile } from "@/services/media";
import type { UploadResult } from "@/types/media";

/**
 * Drag-and-drop or click to upload one or more images. Files upload one at a
 * time; each failure is reported individually and never stops the others.
 */
export function UploadZone({
  onUpload,
  onDone,
  compact,
  label = "Add photos",
}: {
  onUpload: (file: File) => Promise<UploadResult>;
  onDone?: (results: UploadResult[]) => void;
  compact?: boolean;
  label?: string;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

  const handle = async (files: File[]) => {
    if (!files.length || progress) return;
    const valid: File[] = [];
    for (const f of files) {
      const problem = precheckFile(f);
      if (problem) toast.error(problem);
      else valid.push(f);
    }
    if (!valid.length) return;
    const results: UploadResult[] = [];
    setProgress({ done: 0, total: valid.length });
    for (const [i, file] of valid.entries()) {
      try {
        const r = await onUpload(file);
        results.push(r);
        if (!r.created) toast.info(`${file.name}: this image was already in the library, so it was reused.`);
      } catch (e) {
        toast.error(`${file.name}: ${e instanceof ApiError ? e.message : "upload failed"}`);
      }
      setProgress({ done: i + 1, total: valid.length });
    }
    setProgress(null);
    if (results.length) toast.success(`${results.length} image${results.length === 1 ? "" : "s"} uploaded`);
    onDone?.(results);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); void handle([...e.dataTransfer.files]); }}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed text-center transition-colors",
        compact ? "px-4 py-4" : "px-6 py-8",
        dragging ? "border-brand-teal bg-accent" : "border-border bg-muted/30",
      )}
    >
      {progress ? (
        <p className="flex items-center gap-2 text-sm font-medium" role="status">
          <Loader2 className="size-4 animate-spin" aria-hidden /> Uploading {progress.done + 1 > progress.total ? progress.total : progress.done + 1} of {progress.total}…
        </p>
      ) : (
        <>
          <ImagePlus className="size-5 text-muted-foreground" aria-hidden />
          <p className="text-sm">
            <button type="button" onClick={() => input.current?.click()} className="font-medium text-brand-teal hover:underline focus-visible:underline focus-visible:outline-none">
              {label}
            </button>{" "}
            <span className="text-muted-foreground">or drag them here</span>
          </p>
          <p className="text-xs text-muted-foreground">JPG, PNG or WEBP · up to {MAX_UPLOAD_MB} MB each · location data is removed automatically</p>
        </>
      )}
      <input
        ref={input}
        type="file"
        accept={ACCEPT_ATTR}
        multiple
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(e) => { void handle([...(e.target.files ?? [])]); e.target.value = ""; }}
      />
    </div>
  );
}
