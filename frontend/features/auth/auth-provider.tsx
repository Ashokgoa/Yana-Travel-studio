"use client";

import { createContext, useCallback, useContext, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/services/api";
import { authApi } from "@/services/crm";
import type { RoleCode, User } from "@/types/crm";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  error: ApiError | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  hasRole: (...roles: RoleCode[]) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);
export const ME_QUERY_KEY = ["auth", "me"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ME_QUERY_KEY, queryFn: authApi.me, retry: false, staleTime: 5 * 60_000 });

  const user = me.data ?? null;
  const error = me.error instanceof ApiError && me.error.status !== 401 ? me.error : null;

  // Drop every cached query EXCEPT the session one. (queryClient.clear() would also
  // remove the "me" query that this provider is subscribed to, so the new session
  // would never reach the UI until a page refresh.)
  const clearOtherData = useCallback(
    () => queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== ME_QUERY_KEY[0] }),
    [queryClient],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const signedIn = await authApi.login(email, password);
      clearOtherData();
      queryClient.setQueryData(ME_QUERY_KEY, signedIn);
      return signedIn;
    },
    [queryClient, clearOtherData],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clearOtherData();
      queryClient.setQueryData(ME_QUERY_KEY, null);
    }
  }, [queryClient, clearOtherData]);

  const hasRole = useCallback((...roles: RoleCode[]) => !!user && roles.includes(user.role.code), [user]);

  return (
    <AuthContext.Provider value={{ user, loading: me.isPending, error, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Redirects to /login when signed out; shows nothing until the session is known. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading, error } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user && !error) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, error, router, pathname]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-center">
        <div>
          <p className="font-medium text-destructive">Cannot connect to YANA Travel Studio</p>
          <p className="mt-1 text-sm text-muted-foreground">{error.message}</p>
        </div>
      </div>
    );
  }
  if (loading || !user) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  }
  return <>{children}</>;
}

/** Renders children only for the given roles; otherwise a friendly message. */
export function RoleGate({ roles, children }: { roles: RoleCode[]; children: React.ReactNode }) {
  const { hasRole } = useAuth();
  if (!hasRole(...roles)) {
    return (
      <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
        You don&apos;t have permission to view this page.
      </div>
    );
  }
  return <>{children}</>;
}
