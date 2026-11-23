import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { RequireAuth } from "@/features/auth/auth-provider";

function Loading() {
  return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>;
}

/**
 * Every page in this group requires a signed-in user. The session (and the
 * pathname used for the post-login redirect) is only known in the browser, so
 * the group renders inside a Suspense boundary (Next 16 requirement for
 * dynamic client hooks during prerendering). Because of this, each page in the
 * group sets `export const instant = false` (Next validates that per page).
 */
export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<Loading />}>
      <RequireAuth>
        <AppShell>{children}</AppShell>
      </RequireAuth>
    </Suspense>
  );
}
