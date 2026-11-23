import type { EnquiryStatus } from "@/types/crm";

export const ENQUIRY_STATUS_LABELS: Record<EnquiryStatus, string> = {
  new: "New",
  in_progress: "In Progress",
  proposal_generated: "Proposal Generated",
  sent_to_agent: "Sent to Agent",
  revision_requested: "Revision Requested",
  approved: "Approved",
  booking_confirmed: "Booking Confirmed",
  cancelled: "Cancelled",
};

const dateFormatter = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" });
const dateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Formats an ISO date (YYYY-MM-DD) without timezone shifting. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return dateFormatter.format(new Date(y, m - 1, d));
}

export function formatDateTime(value: string | null | undefined): string {
  return value ? dateTimeFormatter.format(new Date(value)) : "—";
}

export function formatMoney(amount: string | number | null | undefined, currency: string): string {
  if (amount === null || amount === undefined || amount === "") return "—";
  try {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(amount));
  } catch {
    return `${amount} ${currency}`;
  }
}

/** Inclusive day/night count for a trip, e.g. 1–15 June = 15 days / 14 nights. */
export function tripLength(start: string | null, end: string | null): { days: number; nights: number } | null {
  if (!start || !end) return null;
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (Number.isNaN(ms) || ms < 0) return null;
  const nights = Math.round(ms / 86_400_000);
  return { days: nights + 1, nights };
}

export function todayIso(): string {
  const now = new Date();
  const tz = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - tz).toISOString().slice(0, 10);
}

/** Empty string → null; used when sending optional form fields. */
export function emptyToNull(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}
