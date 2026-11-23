import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/common/page-header";
import { EnquiryForm } from "@/features/crm/enquiries/enquiry-form";

export const metadata: Metadata = { title: "New Enquiry" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        back={{ href: "/crm/enquiries", label: "Enquiries" }}
        title="New enquiry"
        description="Log an incoming request from a travel agent. Detailed travel requirements are captured in the next step."
      />
      <Suspense>
        <EnquiryForm />
      </Suspense>
    </div>
  );
}
