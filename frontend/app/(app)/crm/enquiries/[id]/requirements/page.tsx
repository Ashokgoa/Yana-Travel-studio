import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { RequirementsWizard } from "@/features/requirements/requirements-wizard";

export const metadata: Metadata = { title: "Customer Requirements" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id < 1) notFound();
  return (
    <Suspense>
      <RequirementsWizard enquiryId={id} />
    </Suspense>
  );
}
