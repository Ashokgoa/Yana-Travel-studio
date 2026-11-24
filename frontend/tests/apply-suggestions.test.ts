import { describe, expect, it } from "vitest";
import { applySuggestions } from "@/features/requirements/apply-suggestions";
import type { FieldSuggestion } from "@/services/ai";
import type { RequirementInput } from "@/types/requirements";

const s = (field: string, value: unknown, merge: FieldSuggestion["merge"]): FieldSuggestion =>
  ({ field, label: field, value, display: "", merge, evidence: null, current: null, overwrites: false });

describe("applySuggestions", () => {
  const draft = {
    adults: 2, interests: ["museums"], destinations: [{ country_id: 1, city_id: null, preference: "mandatory", min_nights: null }],
    additional_requirements: "Late check-out",
  } as unknown as RequirementInput;

  it("replaces, unions lists, appends destinations and text", () => {
    const patch = applySuggestions(draft, [
      s("adults", 4, "replace"),
      s("interests", ["museums", "lakes"], "union"),
      s("destinations", [{ country_id: 2, city_id: 7, preference: "mandatory", min_nights: null }], "append"),
      s("additional_requirements", "Wheelchair at airports", "append"),
    ]);
    expect(patch.adults).toBe(4);
    expect(patch.interests).toEqual(["museums", "lakes"]);
    expect(patch.destinations?.map((d) => d.country_id)).toEqual([1, 2]);
    expect(patch.additional_requirements).toBe("Late check-out\nWheelchair at airports");
  });

  it("starts empty text and lists cleanly", () => {
    const patch = applySuggestions({ ...draft, additional_requirements: null, interests: [] } as unknown as RequirementInput,
      [s("additional_requirements", "Anniversary", "append"), s("interests", ["family"], "union")]);
    expect(patch.additional_requirements).toBe("Anniversary");
    expect(patch.interests).toEqual(["family"]);
  });
});
