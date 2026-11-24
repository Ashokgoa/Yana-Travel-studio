import type { Metadata } from "next";
import { RoleGate } from "@/features/auth/auth-provider";
import { DataAdmin } from "@/features/admin/data-admin";

export const metadata: Metadata = { title: "Backups & data" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return (
    <RoleGate roles={["admin"]}>
      <DataAdmin />
    </RoleGate>
  );
}
