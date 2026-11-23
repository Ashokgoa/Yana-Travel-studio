import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CustomerDetail } from "@/features/crm/customers/customer-detail";

export const metadata: Metadata = { title: "Customer" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id < 1) notFound();
  return <CustomerDetail id={id} />;
}
