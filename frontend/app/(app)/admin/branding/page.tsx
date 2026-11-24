import type { Metadata } from "next";
import { RoleGate } from "@/features/auth/auth-provider";
import { BrandingAdmin } from "@/features/admin/branding-admin";

export const metadata: Metadata = { title: "Branding and PDF defaults" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return (
    <RoleGate roles={["admin"]}>
      <BrandingAdmin />
    </RoleGate>
  );
}
