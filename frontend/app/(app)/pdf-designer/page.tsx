import type { Metadata } from "next";
import { PdfDesignerHome } from "@/features/proposal/pdf-designer-home";

export const metadata: Metadata = { title: "PDF Designer" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <PdfDesignerHome />;
}
