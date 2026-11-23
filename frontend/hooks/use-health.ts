"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, systemApi } from "@/services/api";
import type { HealthResponse } from "@/types/api";

type State = { data?: HealthResponse; error?: string; loading: boolean };

export function useHealth() {
  const [state, setState] = useState<State>({ loading: true });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    try {
      setState({ data: await systemApi.health(), loading: false });
    } catch (e) {
      setState({ error: e instanceof ApiError ? e.message : "Unexpected error", loading: false });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch on mount
    void refresh();
  }, [refresh]);

  return { ...state, refresh };
}
