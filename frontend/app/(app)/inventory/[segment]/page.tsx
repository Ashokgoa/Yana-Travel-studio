import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { InventoryList } from "@/features/inventory/inventory-list";
import { RESOURCE_BY_SEGMENT, RESOURCES } from "@/features/inventory/resource-config";

// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

type Props = { params: Promise<{ segment: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const key = RESOURCE_BY_SEGMENT[(await params).segment];
  return { title: key ? RESOURCES[key].title : "Inventory" };
}

export default async function Page({ params }: Props) {
  const key = RESOURCE_BY_SEGMENT[(await params).segment];
  if (!key) notFound();
  return <InventoryList resource={key} />;
}
