import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ProposalDesigner } from "@/features/proposal/proposal-designer";

export const metadata: Metadata = { title: "PDF proposal" };
// Waits for the browser-side session check (see app/(app)/layout.tsx), so not "instant".
export const instant = false;

type Props = { params: Promise<{ id: string }>; searchParams: Promise<{ version?: string }> };

export default async function Page({ params, searchParams }: Props) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id < 1) notFound();
  const raw = (await searchParams).version;
  const version = raw && /^\d+$/.test(raw) ? Number(raw) : undefined;
  return <ProposalDesigner key={version ?? "latest"} id={id} version={version} />;
}
