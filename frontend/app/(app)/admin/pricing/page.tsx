import type { Metadata } from "next";
import { RoleGate } from "@/features/auth/auth-provider";
import { PricingDefaultsAdmin } from "@/features/admin/pricing-defaults-admin";

export const metadata: Metadata = { title: "Pricing defaults" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return (
    <RoleGate roles={["admin"]}>
      <PricingDefaultsAdmin />
    </RoleGate>
  );
}
