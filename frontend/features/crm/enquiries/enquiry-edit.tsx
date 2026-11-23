"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, TableSkeleton } from "@/components/common/states";
import { EnquiryForm } from "@/features/crm/enquiries/enquiry-form";
import { enquiriesApi } from "@/services/crm";

export function EnquiryEdit({ id }: { id: number }) {
  const query = useQuery({ queryKey: ["enquiries", "detail", id], queryFn: () => enquiriesApi.get(id) });
  if (query.isPending) return <TableSkeleton rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader back={{ href: `/crm/enquiries/${id}`, label: query.data.reference }} title={`Edit ${query.data.reference}`} />
      <EnquiryForm enquiry={query.data} />
    </div>
  );
}
