"use client";

import { CheckCircle2, Database, FolderOpen, RefreshCw, Server, TriangleAlert, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useHealth } from "@/hooks/use-health";
import type { ComponentStatus } from "@/types/api";

function StatusRow({ icon: Icon, label, status }: { icon: typeof Server; label: string; status?: ComponentStatus }) {
  const ok = status?.status === "ok";
  return (
    <div className="flex items-start gap-3 rounded-lg border bg-muted/40 px-4 py-3">
      <Icon className="mt-0.5 size-4 text-muted-foreground" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{label}</p>
        <p className="truncate text-xs text-muted-foreground">{status?.detail ?? "—"}</p>
      </div>
      {status &&
        (ok ? (
          <CheckCircle2 className="size-4 text-success" aria-label="OK" />
        ) : (
          <XCircle className="size-4 text-destructive" aria-label="Error" />
        ))}
    </div>
  );
}

export function SystemStatusCard() {
  const { data, error, loading, refresh } = useHealth();

  return (
    <Card>
      <CardHeader>
        <CardTitle>System status</CardTitle>
        <CardDescription>Local backend, database and file storage</CardDescription>
        <CardAction>
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
            <RefreshCw className={loading ? "animate-spin" : undefined} aria-hidden />
            Refresh
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-3">
        {error ? (
          <div role="alert" className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
            <TriangleAlert className="mt-0.5 size-4 text-destructive" aria-hidden />
            <div className="text-sm">
              <p className="font-medium text-destructive">Backend unavailable</p>
              <p className="text-muted-foreground">{error}</p>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">API</span>
              {data ? (
                <Badge variant={data.status === "ok" ? "default" : "destructive"}>
                  {data.status === "ok" ? "Operational" : "Degraded"}
                </Badge>
              ) : (
                <Badge variant="secondary">Checking…</Badge>
              )}
              {data && <span className="text-xs text-muted-foreground">v{data.version} · {data.environment}</span>}
            </div>
            <StatusRow icon={Database} label="Database" status={data?.database} />
            <StatusRow icon={FolderOpen} label="Image storage" status={data?.storage} />
            <StatusRow icon={Server} label="Exports folder" status={data?.exports} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
