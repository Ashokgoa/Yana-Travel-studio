import type { Metadata } from "next";
import { Dashboard } from "@/features/dashboard/dashboard";

export const metadata: Metadata = { title: "Dashboard" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

export default function DashboardPage() {
  return <Dashboard />;
}
