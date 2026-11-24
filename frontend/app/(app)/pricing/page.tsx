import type { Metadata } from "next";
import { PricingHome } from "@/features/pricing/pricing-home";

export const metadata: Metadata = { title: "Pricing & Costing" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <PricingHome />;
}
