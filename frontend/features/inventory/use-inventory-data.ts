"use client";

import { useQuery } from "@tanstack/react-query";
import { inventoryApi } from "@/services/inventory";
import type { InventoryItem } from "@/types/inventory";
import type { FieldDef, RefSource } from "@/features/inventory/resource-config";

export type RefOption = { value: string; label: string; group?: string; inactive?: boolean };

const PAGE = { page_size: 100 };

export function useInventoryOptions() {
  return useQuery({ queryKey: ["inventory", "options"], queryFn: inventoryApi.options, staleTime: Infinity });
}

/** Options for a reference dropdown (cities grouped by country). Includes inactive rows, flagged. */
export function useRefOptions(ref: RefSource | undefined, enabled = true) {
  return useQuery({
    queryKey: ["inventory", "ref-options", ref],
    enabled: Boolean(ref) && enabled,
    staleTime: 60_000,
    queryFn: async (): Promise<RefOption[]> => {
      switch (ref) {
        case "countries":
          return (await inventoryApi.list("countries", PAGE)).items.map((c) => ({
            value: String(c.id), label: c.name, inactive: !c.is_active,
          }));
        case "cities":
          return (await inventoryApi.list("cities", PAGE)).items
            .map((c) => ({ value: String(c.id), label: c.name, group: c.country?.name ?? "", inactive: !c.is_active }))
            .sort((a, b) => a.group.localeCompare(b.group) || a.label.localeCompare(b.label));
        case "suppliers":
          return (await inventoryApi.list("suppliers", PAGE)).items.map((s) => ({
            value: String(s.id), label: s.name, inactive: !s.is_active,
          }));
        case "vehicleCategories":
          return (await inventoryApi.vehicleCategories()).map((c) => ({ value: String(c.id), label: `${c.name} (${c.passenger_capacity} seats)` }));
        default:
          return [];
      }
    },
  });
}

// ------------------------------------------------------------------ form <-> API conversion
export type FormValue = string | boolean | string[];

export function toFormValue(field: FieldDef, item?: InventoryItem): FormValue {
  const raw = item ? (field.get ? field.get(item) : item[field.name]) : undefined;
  switch (field.type) {
    case "bool":
      return raw === true;
    case "multi":
      return Array.isArray(raw) ? raw.map(String) : [];
    case "multiref":
      return Array.isArray(raw) ? raw.map(String) : [];
    case "tristate":
      return raw === true ? "true" : raw === false ? "false" : "";
    case "currency":
      return (raw as string) ?? "EUR";
    default:
      return raw === null || raw === undefined ? "" : String(raw);
  }
}

export function toApiValue(field: FieldDef, value: FormValue): unknown {
  switch (field.type) {
    case "bool":
      return Boolean(value);
    case "multi":
      return value as string[];
    case "multiref":
      return (value as string[]).map(Number);
    case "tristate":
      return value === "true" ? true : value === "false" ? false : null;
    case "int":
    case "reference":
      return value === "" ? null : Number(value);
    case "float":
      return value === "" ? null : Number(String(value).replace(",", "."));
    case "decimal":
      return value === "" ? null : String(value).replace(",", ".");
    case "select":
      if (value === "") return null;
      return field.name === "star_rating" ? Number(value) : value;
    default: {
      const s = String(value).trim();
      return s === "" ? null : s;
    }
  }
}

/** Client-side checks for obvious mistakes; the server performs full validation. */
export function validateField(field: FieldDef, value: FormValue): string | undefined {
  const empty = value === "" || (Array.isArray(value) && value.length === 0);
  if (field.required && empty && field.type !== "bool") return `${field.label} is required`;
  if (empty || typeof value !== "string") return;
  const v = value.trim().replace(",", ".");
  if (field.type === "int" && !/^\d+$/.test(v)) return "Enter a whole number";
  if (field.type === "decimal" && !/^\d+(\.\d{1,2})?$/.test(v)) return "Enter an amount, e.g. 120 or 120.50";
  if (field.type === "float" && !/^-?\d+(\.\d+)?$/.test(v)) return "Enter a number, e.g. 52.3676";
  if (field.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return "Enter a valid email address";
}
