import type { Metadata } from "next";
import { RoleGate } from "@/features/auth/auth-provider";
import { AIAdmin } from "@/features/admin/ai-admin";

export const metadata: Metadata = { title: "AI assistant" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return (
    <RoleGate roles={["admin"]}>
      <AIAdmin />
    </RoleGate>
  );
}
