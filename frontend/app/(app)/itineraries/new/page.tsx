import type { Metadata } from "next";
import { CreateItineraryPage } from "@/features/itinerary-builder/create-itinerary-page";

export const metadata: Metadata = { title: "Create Itinerary" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <CreateItineraryPage />;
}
