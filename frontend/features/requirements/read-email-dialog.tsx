"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CloudUpload, Loader2, MonitorCheck, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { aiApi, type FieldSuggestion, type ReadResult } from "@/services/ai";
import { ApiError } from "@/services/api";

export function ReadEmailDialog({ enquiryId, open, onOpenChange, onApply }: {
  enquiryId: number; open: boolean; onOpenChange: (o: boolean) => void; onApply: (picked: FieldSuggestion[]) => void;
}) {
  const status = useQuery({ queryKey: ["ai", "status"], queryFn: aiApi.status, enabled: open, staleTime: 60_000 });
  const [text, setText] = useState("");
  const [result, setResult] = useState<ReadResult | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const read = useMutation({
    mutationFn: () => aiApi.readText(enquiryId, text),
    onSuccess: (r) => {
      setResult(r);
      setPicked(new Set(r.suggestions.filter((s) => !s.overwrites).map((s) => s.field)));
      if (!r.suggestions.length) toast.info("Nothing new found in this text.");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not read the text"),
  });
  const close = (o: boolean) => {
    onOpenChange(o);
    if (!o) { setResult(null); setText(""); }
  };
  const offDevice = status.data?.sends_data_off_device;

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Sparkles className="size-4 text-brand-teal" aria-hidden /> Read requirements from an email</DialogTitle>
          <DialogDescription>Paste the agent&apos;s email or notes. You&apos;ll see what was found and choose what to use; nothing is saved until you save the requirements.</DialogDescription>
        </DialogHeader>
        {status.data && (
          <p className={cn("flex items-start gap-2 rounded-md px-3 py-2 text-xs", offDevice ? "bg-amber-50 text-amber-900" : "bg-emerald-50 text-emerald-900")}>
            {offDevice ? <CloudUpload className="mt-0.5 size-4 shrink-0" aria-hidden /> : <MonitorCheck className="mt-0.5 size-4 shrink-0" aria-hidden />}
            {offDevice ? `${status.data.label}: the pasted text is sent to Anthropic to be read.` : `${status.data.label}: nothing is sent anywhere.`}
          </p>
        )}
        {!result ? (
          <Textarea aria-label="Email or notes" rows={12} value={text} onChange={(e) => setText(e.target.value)} maxLength={20000}
            placeholder={"e.g. We have a family of 6 (4 adults, 2 kids aged 8 and 12) arriving in Amsterdam on 1 June 2027 for 15 days, departing Zurich. 4* hotels, Indian vegetarian food, private coach, budget EUR 3,000 per person…"} />
        ) : (
          <div className="max-h-[55vh] space-y-3 overflow-y-auto pr-1">
            {result.fallback_note && <p className="flex gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900"><AlertTriangle className="size-4 shrink-0" aria-hidden />{result.fallback_note}</p>}
            {result.unmatched_places.length > 0 && (
              <p className="flex gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900"><AlertTriangle className="size-4 shrink-0" aria-hidden />
                Not in Destination Inventory (add them there first, or handle manually): {result.unmatched_places.join(", ")}</p>
            )}
            <ul className="divide-y rounded-lg border" aria-label="Found in the text">
              {result.suggestions.map((s) => (
                <li key={s.field} className="flex items-start gap-3 p-3">
                  <input type="checkbox" className="mt-1 size-4" id={`rs-${s.field}`} checked={picked.has(s.field)}
                    onChange={(e) => { const on = e.target.checked; setPicked((p) => { const n = new Set(p); if (on) n.add(s.field); else n.delete(s.field); return n; }); }} />
                  <label htmlFor={`rs-${s.field}`} className="min-w-0 flex-1 text-sm">
                    <span className="font-medium">{s.label}: </span>{s.display}
                    {s.current && <span className={cn("block text-xs", s.overwrites ? "text-amber-800" : "text-muted-foreground")}>
                      {s.overwrites ? "Replaces" : s.merge === "replace" ? "Currently" : "Adds to"}: {s.current}</span>}
                    {s.evidence && <span className="block text-xs text-muted-foreground italic">“{s.evidence}”</span>}
                  </label>
                </li>
              ))}
              {!result.suggestions.length && <li className="p-3 text-sm text-muted-foreground">Nothing new found.</li>}
            </ul>
            <p className="text-xs text-muted-foreground">Read by: {result.provider_label}. Always check the values; the reader can miss or misread things.</p>
          </div>
        )}
        <DialogFooter>
          {!result ? (
            <Button onClick={() => read.mutate()} disabled={text.trim().length < 10 || read.isPending}>
              {read.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <Sparkles aria-hidden />} Read
            </Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => setResult(null)}>Back to text</Button>
              <Button disabled={!picked.size} onClick={() => {
                onApply(result.suggestions.filter((s) => picked.has(s.field)));
                close(false);
              }}>Use {picked.size} selected</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
