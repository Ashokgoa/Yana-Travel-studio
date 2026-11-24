import type { Metadata } from "next";
import { SavedItineraries } from "@/features/itineraries/saved-itineraries";

export const metadata: Metadata = { title: "Saved Itineraries" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <SavedItineraries />;
}
