import type { Metadata } from "next";
import { InventoryList } from "@/features/inventory/inventory-list";

export const metadata: Metadata = { title: "Suppliers" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <InventoryList resource="suppliers" />;
}
