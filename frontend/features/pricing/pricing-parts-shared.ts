import type { PricingView } from "@/types/pricing";

export type Run = (fn: () => Promise<PricingView>, success?: string) => void;

export function money(amount: string | number | null | undefined, currency: string, decimals = 2): string {
  if (amount === null || amount === undefined || amount === "") return "—";
  try {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency, minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(Number(amount));
  } catch {
    return `${amount} ${currency}`;
  }
}
