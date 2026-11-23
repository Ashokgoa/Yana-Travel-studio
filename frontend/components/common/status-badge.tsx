import { ENQUIRY_STATUS_LABELS } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AgentStatus, EnquiryStatus } from "@/types/crm";

const ENQUIRY_STYLES: Record<EnquiryStatus, string> = {
  new: "bg-sky-50 text-sky-700 ring-sky-600/20",
  in_progress: "bg-amber-50 text-amber-800 ring-amber-600/20",
  proposal_generated: "bg-violet-50 text-violet-700 ring-violet-600/20",
  sent_to_agent: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
  revision_requested: "bg-orange-50 text-orange-700 ring-orange-600/20",
  approved: "bg-teal-50 text-teal-700 ring-teal-600/20",
  booking_confirmed: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  cancelled: "bg-zinc-100 text-zinc-600 ring-zinc-500/20",
};

// font-sans + tracking-normal: badges often sit inside headings, which use the display serif.
const pill = "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-sans text-xs font-medium tracking-normal whitespace-nowrap ring-1 ring-inset";

export function EnquiryStatusBadge({ status }: { status: EnquiryStatus }) {
  return (
    <span className={cn(pill, ENQUIRY_STYLES[status])}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {ENQUIRY_STATUS_LABELS[status]}
    </span>
  );
}

export function ActiveBadge({ status }: { status: AgentStatus | boolean }) {
  const active = status === true || status === "active";
  return (
    <span className={cn(pill, active ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20" : "bg-zinc-100 text-zinc-600 ring-zinc-500/20")}>
      {active ? "Active" : "Inactive"}
    </span>
  );
}
