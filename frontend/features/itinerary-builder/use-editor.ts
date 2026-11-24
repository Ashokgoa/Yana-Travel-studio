"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "@/services/api";
import type { ItineraryDetail } from "@/types/itinerary";

export const detailKey = (id: number) => ["itineraries", "detail", id];

/** Runs one builder operation; the server returns the updated itinerary, which replaces the cached one. */
export function useEditor(itineraryId: number) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (op: { run: () => Promise<ItineraryDetail>; success?: string }) => op.run(),
    onSuccess: (detail, op) => {
      queryClient.setQueryData(detailKey(itineraryId), detail);
      queryClient.invalidateQueries({ queryKey: ["itineraries", "versions", itineraryId] });
      queryClient.invalidateQueries({ queryKey: ["itineraries", "enquiry"] });
      queryClient.invalidateQueries({ queryKey: ["itineraries", "list"] });
      if (op.success) toast.success(op.success);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "The change could not be saved. Please try again."),
  });
  return {
    run: (run: () => Promise<ItineraryDetail>, success?: string) => mutation.mutate({ run, success }),
    pending: mutation.isPending,
  };
}
