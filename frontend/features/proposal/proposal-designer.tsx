"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, FileDown, Info, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/states";
import { Button, buttonVariants } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { itinerariesApi } from "@/services/itineraries";
import { proposalsApi } from "@/services/proposals";
import type { ProposalSettings } from "@/types/proposal";
import { ListsPanel, Panel, PhotosPanel, PricePanel, SectionsPanel, TemplatePanel, TextPanel } from "./designer-panels";

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function download(url: string) {
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

const sizeText = (bytes: number) => (bytes > 1_048_576 ? `${(bytes / 1_048_576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

export function ProposalDesigner({ id, version }: { id: number; version?: number }) {
  const qc = useQueryClient();
  const itinerary = useQuery({ queryKey: ["itineraries", "detail", id, version ?? "latest"], queryFn: () => itinerariesApi.get(id, version) });
  const saved = useQuery({ queryKey: ["proposal", id, "settings"], queryFn: () => proposalsApi.settings(id) });
  const options = useQuery({ queryKey: ["proposal", id, "options", version ?? "latest"], queryFn: () => proposalsApi.options(id, version) });
  const history = useQuery({ queryKey: ["proposal", id, "exports"], queryFn: () => proposalsApi.exports(id) });

  // Local draft of the settings; `null` until the saved settings have loaded.
  const [draft, setDraft] = useState<ProposalSettings | null>(null);
  const [baseline, setBaseline] = useState<string>("");
  if (draft === null && saved.data) {
    setDraft(saved.data);
    setBaseline(JSON.stringify(saved.data));
  }
  const change = (patch: Partial<ProposalSettings>) => setDraft((d) => (d ? { ...d, ...patch } : d));
  const dirty = draft !== null && JSON.stringify(draft) !== baseline;

  const debounced = useDebounced(draft, 500);
  const previewKey = useMemo(() => JSON.stringify(debounced), [debounced]);
  const preview = useQuery({
    queryKey: ["proposal", id, "preview", version ?? "latest", previewKey],
    queryFn: ({ signal }) => proposalsApi.preview(id, debounced!, version, signal),
    enabled: debounced !== null,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

  const save = useMutation({
    mutationFn: () => proposalsApi.saveSettings(id, draft!),
    onSuccess: (s) => {
      setBaseline(JSON.stringify(s));
      qc.setQueryData(["proposal", id, "settings"], s);
      toast.success("PDF settings saved for this itinerary");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save the settings"),
  });

  const create = useMutation({
    mutationFn: () => proposalsApi.exportPdf(id, draft!, version),
    onSuccess: (e) => {
      setBaseline(JSON.stringify(draft));
      toast.success(`PDF created: ${e.filename}`);
      download(proposalsApi.fileUrl(id, e.id));
      void qc.invalidateQueries({ queryKey: ["proposal", id] });
      void qc.invalidateQueries({ queryKey: ["itineraries"] });
      void qc.invalidateQueries({ queryKey: ["enquiries"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not create the PDF"),
  });

  // Warn before leaving with unsaved settings.
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const failed = itinerary.error ?? options.error ?? saved.error;
  if (failed) return <ErrorState message={failed instanceof ApiError ? failed.message : "Could not load the PDF designer."} onRetry={() => { void itinerary.refetch(); void options.refetch(); void saved.refetch(); }} />;
  if (!itinerary.data || !options.data || !draft) return <p className="text-sm text-muted-foreground">Loading the PDF designer…</p>;

  const it = itinerary.data;
  const opt = options.data;
  const previewing = preview.isFetching || JSON.stringify(draft) !== previewKey;

  return (
    <div className="space-y-4">
      <PageHeader
        title="PDF proposal"
        description={`${it.title} · ${it.customer_name ?? ""} · from version ${opt.version_number} (${opt.version_label})`}
        actions={
          <>
            <Link href={`/itineraries/${id}${version ? `?version=${version}` : ""}`} className={buttonVariants({ variant: "outline" })}><ArrowLeft aria-hidden /> Itinerary</Link>
            <Button variant="outline" onClick={() => save.mutate()} disabled={!dirty || save.isPending}><Save aria-hidden /> Save settings</Button>
            <Button onClick={() => create.mutate()} disabled={create.isPending}>
              {create.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <FileDown aria-hidden />}
              {create.isPending ? "Creating PDF…" : "Create PDF"}
            </Button>
          </>
        }
      />
      {!opt.version_is_locked && (
        <p className="flex items-start gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          Version {opt.version_number} is a working draft. Creating the PDF first saves it as a read-only version named “PDF proposal”, so the PDF always matches a saved version.
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="space-y-5 rounded-xl border bg-card p-4 lg:max-h-[calc(100vh-11rem)] lg:overflow-y-auto" aria-label="PDF settings">
          <TemplatePanel s={draft} options={opt} onChange={change} />
          <SectionsPanel s={draft} options={opt} onChange={change} />
          <PricePanel s={draft} options={opt} onChange={change} pricingHref={`/itineraries/${id}/pricing${version ? `?version=${version}` : ""}`} />
          <TextPanel s={draft} options={opt} onChange={change} />
          <PhotosPanel s={draft} options={opt} onChange={change} />
          <ListsPanel s={draft} options={opt} onChange={change} />
          <Panel title="PDFs created">
            {history.data?.length ? (
              <ul className="space-y-2 text-sm" aria-label="PDFs created">
                {history.data.map((e) => (
                  <li key={e.id} className="flex items-start gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium" title={e.filename}>{e.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        Version {e.version_number} · {e.template} · {formatDateTime(e.created_at)}{e.created_by_name ? ` · ${e.created_by_name}` : ""} · {sizeText(e.size_bytes)}
                      </p>
                    </div>
                    <a href={proposalsApi.fileUrl(id, e.id)} className={buttonVariants({ size: "icon-sm", variant: "ghost" })} aria-label={`Download ${e.filename}`}>
                      <Download aria-hidden />
                    </a>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-muted-foreground">No PDF yet.</p>}
          </Panel>
        </aside>

        <section aria-label="Preview" className="relative overflow-hidden rounded-xl border bg-[#e9e9e9]">
          <div className={cn("absolute top-2 right-3 z-10 inline-flex items-center gap-1.5 rounded-full bg-background/90 px-2.5 py-1 text-xs shadow transition-opacity", previewing ? "opacity-100" : "opacity-0")} role="status" aria-live="polite">
            <Loader2 className="size-3.5 animate-spin" aria-hidden /> Updating preview…
          </div>
          {preview.error ? (
            <div className="p-6"><ErrorState message={preview.error instanceof ApiError ? preview.error.message : "Preview failed"} onRetry={() => void preview.refetch()} /></div>
          ) : preview.data ? (
            // Static HTML with embedded images; sandboxed with scripts disabled.
            <iframe title="PDF preview" sandbox="" srcDoc={preview.data} className="h-[calc(100vh-11rem)] min-h-[600px] w-full bg-[#e9e9e9]" />
          ) : <p className="p-6 text-sm text-muted-foreground">Preparing preview…</p>}
          <p className="sr-only">The preview shows page breaks as dashed lines; the PDF is A4 with page numbers.</p>
        </section>
      </div>
    </div>
  );
}
