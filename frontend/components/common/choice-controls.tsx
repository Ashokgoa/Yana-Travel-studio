"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type Choice = { value: string; label: string };

/** Multi-select as toggle chips (aria-pressed). */
export function ChipGroup({
  id,
  options,
  value,
  onChange,
  label,
}: {
  id?: string;
  options: Choice[];
  value: string[];
  onChange: (v: string[]) => void;
  label?: string;
}) {
  return (
    <div id={id} role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const on = value.includes(o.value);
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(on ? value.filter((v) => v !== o.value) : [...value, o.value])}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors",
              "focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
              on ? "border-brand-teal bg-accent font-medium text-accent-foreground" : "bg-background text-muted-foreground hover:text-foreground",
            )}
          >
            {on && <Check className="size-3.5" aria-hidden />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/** Single choice as a segmented control (radiogroup). `""` can be used as an explicit "unset" option. */
export function Segmented({
  id,
  options,
  value,
  onChange,
  label,
  size = "md",
}: {
  id?: string;
  options: Choice[];
  value: string;
  onChange: (v: string) => void;
  label?: string;
  size?: "sm" | "md";
}) {
  return (
    <div id={id} role="radiogroup" aria-label={label} className="inline-flex flex-wrap rounded-lg border bg-muted/40 p-0.5">
      {options.map((o) => (
        <button
          key={o.value || "unset"}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-md transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
            size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm",
            value === o.value ? "bg-background font-medium text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Labelled on/off switch built on a checkbox (keyboard and screen-reader friendly). */
export function Toggle({ id, checked, onChange, label, hint }: { id: string; checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  return (
    <label htmlFor={id} className="flex cursor-pointer items-start gap-3">
      <span className="relative mt-0.5 inline-flex">
        <input id={id} type="checkbox" role="switch" className="peer sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className="h-5 w-9 rounded-full bg-muted-foreground/30 transition-colors peer-checked:bg-brand-teal peer-focus-visible:ring-3 peer-focus-visible:ring-ring/50" />
        <span className="absolute top-0.5 left-0.5 size-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-4" />
      </span>
      <span className="text-sm">
        {label}
        {hint && <span className="block text-xs text-muted-foreground">{hint}</span>}
      </span>
    </label>
  );
}
