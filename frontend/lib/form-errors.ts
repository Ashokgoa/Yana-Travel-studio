import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { toast } from "sonner";
import { ApiError } from "@/services/api";

/**
 * Shows backend errors to the user: field-level validation messages go onto the
 * matching form fields; anything else becomes a toast. Never fails silently.
 */
export function handleFormError<T extends FieldValues>(error: unknown, setError?: UseFormSetError<T>, fields?: string[]) {
  if (error instanceof ApiError) {
    const details = error.body?.details ?? [];
    let unplaced = false;
    for (const d of details) {
      const field = d.field.split(".")[0];
      if (setError && field && (!fields || fields.includes(field))) {
        setError(field as Path<T>, { type: "server", message: d.message });
      } else {
        unplaced = true;
      }
    }
    if (details.length === 0 || unplaced) {
      const extra = unplaced ? details.filter((d) => !d.field || (fields && !fields.includes(d.field.split(".")[0]))) : [];
      toast.error(extra.length ? extra.map((d) => d.message).join(" ") : error.message);
    }
    return;
  }
  toast.error("Something went wrong. Please try again.");
}
