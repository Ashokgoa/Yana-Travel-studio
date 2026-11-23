import type { Metadata } from "next";
import { EnquiriesList } from "@/features/crm/enquiries/enquiries-list";

export const metadata: Metadata = { title: "Enquiries" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <EnquiriesList />;
}
