import type { FieldSuggestion } from "@/services/ai";
import type { RequirementInput } from "@/types/requirements";

/** Merge accepted suggestions into the wizard draft (the planner still saves as usual). */
export function applySuggestions(draft: RequirementInput, picked: FieldSuggestion[]): Partial<RequirementInput> {
  const patch: Record<string, unknown> = {};
  const current = draft as unknown as Record<string, unknown>;
  for (const s of picked) {
    const now = patch[s.field] ?? current[s.field];
    if (s.merge === "union" && Array.isArray(s.value)) {
      patch[s.field] = [...new Set([...((now as unknown[]) ?? []), ...s.value])];
    } else if (s.merge === "append" && Array.isArray(s.value)) {
      patch[s.field] = [...((now as unknown[]) ?? []), ...s.value];
    } else if (s.merge === "append" && typeof s.value === "string") {
      patch[s.field] = now ? `${String(now)}\n${s.value}` : s.value;
    } else {
      patch[s.field] = s.value;
    }
  }
  return patch as Partial<RequirementInput>;
}
