import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { InventoryDetail } from "@/features/inventory/inventory-detail";
import { RESOURCE_BY_SEGMENT, RESOURCES } from "@/features/inventory/resource-config";

// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

type Props = { params: Promise<{ segment: string; id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const key = RESOURCE_BY_SEGMENT[(await params).segment];
  return { title: key ? RESOURCES[key].singular : "Inventory" };
}

export default async function Page({ params }: Props) {
  const { segment, id: rawId } = await params;
  const key = RESOURCE_BY_SEGMENT[segment];
  const id = Number(rawId);
  if (!key || !Number.isInteger(id) || id < 1) notFound();
  return <InventoryDetail resource={key} id={id} />;
}
