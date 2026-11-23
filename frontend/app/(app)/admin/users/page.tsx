import type { Metadata } from "next";
import { RoleGate } from "@/features/auth/auth-provider";
import { UsersAdmin } from "@/features/admin/users-admin";

export const metadata: Metadata = { title: "Users" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return (
    <RoleGate roles={["admin"]}>
      <UsersAdmin />
    </RoleGate>
  );
}
