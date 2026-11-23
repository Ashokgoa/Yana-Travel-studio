import type { Metadata } from "next";
import { CustomersList } from "@/features/crm/customers/customers-list";

export const metadata: Metadata = { title: "Customers" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <CustomersList />;
}
