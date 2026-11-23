import type { Metadata } from "next";
import { AgentsList } from "@/features/crm/agents/agents-list";

export const metadata: Metadata = { title: "Travel Agents" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function Page() {
  return <AgentsList />;
}
