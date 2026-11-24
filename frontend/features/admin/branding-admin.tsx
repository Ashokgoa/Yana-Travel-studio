"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Toggle } from "@/components/common/choice-controls";
import { FormField, controlClass } from "@/components/common/form-controls";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { UploadZone } from "@/features/media/upload-zone";
import { API_BASE_URL, ApiError } from "@/services/api";
import { mediaApi } from "@/services/media";
import { proposalsApi } from "@/services/proposals";
import type { BrandingSettings } from "@/types/proposal";

export function BrandingAdmin() {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["settings", "branding"], queryFn: proposalsApi.branding });
  const [draft, setDraft] = useState<BrandingSettings | null>(null);
  if (draft === null && query.data) setDraft(query.data);
  const set = (patch: Partial<BrandingSettings>) => setDraft((d) => (d ? { ...d, ...patch } : d));

  const save = useMutation({
    mutationFn: () => proposalsApi.saveBranding({ ...draft!, default_exclusions: draft!.default_exclusions.map((l) => l.trim()).filter(Boolean) }),
    onSuccess: (b) => {
      setDraft(b);
      qc.setQueryData(["settings", "branding"], b);
      void qc.invalidateQueries({ queryKey: ["proposal"] });
      toast.success("Branding and PDF defaults saved");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save"),
  });

  if (query.error) return <ErrorState message={query.error instanceof ApiError ? query.error.message : "Could not load the branding settings."} onRetry={() => void query.refetch()} />;
  if (!draft) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const dirty = JSON.stringify(draft) !== JSON.stringify(query.data);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Branding and PDF defaults"
        description="Used on every PDF proposal that shows YANA branding, and as the starting texts in the PDF designer."
        actions={<Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}><Save aria-hidden /> Save</Button>}
      />
      {!draft.terms_reviewed && (
        <p className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
          The default terms and conditions are a short placeholder. Replace them with YANA&apos;s own booking conditions, then tick “Terms reviewed”.
        </p>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">YANA brand</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <FormField label="Company name" htmlFor="br-name" required>
              <input id="br-name" className={controlClass} maxLength={120} value={draft.company_name} onChange={(e) => set({ company_name: e.target.value })} />
            </FormField>
            <FormField label="Tagline" htmlFor="br-tagline">
              <input id="br-tagline" className={controlClass} maxLength={200} value={draft.tagline ?? ""} onChange={(e) => set({ tagline: e.target.value || null })} />
            </FormField>
            <FormField label="Contact line" htmlFor="br-contact" hint="Shown at the end of the PDF, e.g. email · phone · website.">
              <input id="br-contact" className={controlClass} maxLength={300} value={draft.contact_line ?? ""} onChange={(e) => set({ contact_line: e.target.value || null })} />
            </FormField>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Logo</p>
              <p className="text-xs text-muted-foreground">Upload YANA&apos;s official logo (PNG with a transparent background works best). It is never generated or recreated.</p>
              {draft.logo_media_id ? (
                <div className="flex items-center gap-3 rounded-lg border p-3">
                  {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                  <img src={`${API_BASE_URL}/media/${draft.logo_media_id}/file`} alt="Current logo" className="max-h-14 max-w-48 object-contain" />
                  <Button variant="ghost" size="sm" className="ml-auto" onClick={() => set({ logo_media_id: null })}><Trash2 aria-hidden /> Remove</Button>
                </div>
              ) : (
                <UploadZone compact label="Upload logo"
                  onUpload={(file) => mediaApi.upload(file, { category: "brand", description: "YANA logo" })}
                  onDone={(results) => { const last = results.at(-1); if (last) set({ logo_media_id: last.media.id }); }} />
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Heading colour" htmlFor="br-primary">
                <input id="br-primary" type="color" className="h-10 w-16 cursor-pointer rounded border p-1" value={draft.primary_color} onChange={(e) => set({ primary_color: e.target.value })} />
              </FormField>
              <FormField label="Accent colour" htmlFor="br-accent">
                <input id="br-accent" type="color" className="h-10 w-16 cursor-pointer rounded border p-1" value={draft.accent_color} onChange={(e) => set({ accent_color: e.target.value })} />
              </FormField>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Default texts</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <FormField label="Closing message" htmlFor="br-closing">
              <Textarea id="br-closing" rows={3} maxLength={1000} value={draft.default_closing} onChange={(e) => set({ default_closing: e.target.value })} />
            </FormField>
            <FormField label="Exclusions" htmlFor="br-exclusions" hint="One per line. Inclusions are generated from each itinerary.">
              <Textarea id="br-exclusions" rows={6} value={draft.default_exclusions.join("\n")} onChange={(e) => set({ default_exclusions: e.target.value.split("\n") })} />
            </FormField>
            <FormField label="Terms and conditions" htmlFor="br-terms" hint="One paragraph per line.">
              <Textarea id="br-terms" rows={7} maxLength={8000} value={draft.default_terms} onChange={(e) => set({ default_terms: e.target.value })} />
            </FormField>
            <Toggle id="br-terms-reviewed" checked={draft.terms_reviewed} onChange={(v) => set({ terms_reviewed: v })}
              label="Terms reviewed" hint="Confirms these are YANA's approved terms." />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
