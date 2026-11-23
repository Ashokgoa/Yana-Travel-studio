import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EnquiryDetailView } from "@/features/crm/enquiries/enquiry-detail";

export const metadata: Metadata = { title: "Enquiry" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id < 1) notFound();
  return <EnquiryDetailView id={id} />;
}
