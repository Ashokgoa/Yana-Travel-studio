import type { Metadata } from "next";
import { MediaLibrary } from "@/features/media/media-library";

export const metadata: Metadata = { title: "Image Library" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <MediaLibrary />;
}
