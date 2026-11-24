import type { Metadata } from "next";
import { TemplatesPage } from "@/features/templates/templates-page";

export const metadata: Metadata = { title: "Itinerary Templates" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <TemplatesPage />;
}
