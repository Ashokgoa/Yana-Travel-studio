"use client";

import { useQuery } from "@tanstack/react-query";
import { CloudUpload, MonitorCheck } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/states";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { aiApi } from "@/services/ai";

/** Read-only: the provider is chosen in the server's .env file, so switching it on is a deliberate, IT-approved step. */
export function AIAdmin() {
  const q = useQuery({ queryKey: ["ai", "status"], queryFn: aiApi.status });
  if (q.error) return <ErrorState message={q.error.message} onRetry={() => void q.refetch()} />;
  if (!q.data) return <p className="text-sm text-muted-foreground">Loading…</p>;
  const s = q.data;
  return (
    <div className="space-y-6">
      <PageHeader title="AI assistant" description="Reads requirements from agents' emails and suggests itinerary improvements. Suggestions are always reviewed by a planner." />
      <Card className={cn(s.sends_data_off_device ? "border-amber-200" : "border-emerald-200")}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            {s.sends_data_off_device ? <CloudUpload className="size-4 text-amber-700" aria-hidden /> : <MonitorCheck className="size-4 text-emerald-700" aria-hidden />}
            Active: {s.label}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>{s.sends_data_off_device
            ? `Pasted email text is sent to Anthropic (model ${s.model}) to be read. Itinerary suggestions still run on this computer.`
            : "Everything runs on this computer: pasted text and itineraries are not sent anywhere."}</p>
          {s.configured_provider === "claude" && !s.claude_sdk_installed && (
            <p className="text-amber-800">Claude is configured but the “anthropic” package is not installed, so the offline reader is used.</p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Using Claude instead (optional)</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>Claude reads unusual or long emails better than the offline reader. It sends the pasted text to Anthropic&apos;s API, so switch it on only with your IT and data-protection approval.</p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>Install the SDK in the backend: <code className="rounded bg-muted px-1">backend\.venv\Scripts\pip install -r backend\requirements-ai.txt</code></li>
            <li>In the project&apos;s <code className="rounded bg-muted px-1">.env</code>: <code className="rounded bg-muted px-1">YANA_AI_PROVIDER=claude</code> and <code className="rounded bg-muted px-1">ANTHROPIC_API_KEY=…</code> (YANA&apos;s own key).</li>
            <li>Restart the app. This page then shows Claude as active. Remove the line to switch it off again.</li>
          </ol>
          <p>If Claude can&apos;t be reached, the offline reader is used automatically and the planner is told.</p>
        </CardContent>
      </Card>
    </div>
  );
}
