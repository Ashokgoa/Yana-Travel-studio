import {
  Building2,
  CalendarCheck,
  Calculator,
  FileText,
  LayoutDashboard,
  Map,
  Route,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { RoleCode } from "@/types/crm";

export type NavItem = {
  label: string;
  href: string;
  icon?: LucideIcon;
  /** Modules are hidden until implemented (PRD 5.2). Flip to true when a phase ships. */
  enabled: boolean;
  /** Restrict to these roles; omitted = every signed-in user. */
  roles?: RoleCode[];
  children?: NavItem[];
};

export const NAVIGATION: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, enabled: true },
  {
    label: "CRM",
    href: "/crm",
    icon: Users,
    enabled: true,
    children: [
      { label: "Travel Agents", href: "/crm/agents", enabled: true },
      { label: "Customers", href: "/crm/customers", enabled: true },
      { label: "Enquiries", href: "/crm/enquiries", enabled: true },
    ],
  },
  {
    label: "Itinerary Builder",
    href: "/itineraries",
    icon: Route,
    enabled: false, // Phases 4–5
    children: [
      { label: "Create Itinerary", href: "/itineraries/new", enabled: false },
      { label: "Saved Itineraries", href: "/itineraries", enabled: false },
      { label: "Itinerary Templates", href: "/itineraries/templates", enabled: false },
      { label: "Compare Proposals", href: "/itineraries/compare", enabled: false },
    ],
  },
  {
    label: "Destination Inventory",
    href: "/inventory",
    icon: Map,
    enabled: true,
    children: [
      { label: "Countries", href: "/inventory/countries", enabled: true },
      { label: "Cities", href: "/inventory/cities", enabled: true },
      { label: "Sightseeing", href: "/inventory/sightseeing", enabled: true },
      { label: "Hotels", href: "/inventory/hotels", enabled: true },
      { label: "Restaurants", href: "/inventory/restaurants", enabled: true },
      { label: "Transportation", href: "/inventory/transportation", enabled: true },
    ],
  },
  { label: "Suppliers", href: "/suppliers", icon: Building2, enabled: true },
  { label: "Pricing & Costing", href: "/pricing", icon: Calculator, enabled: false },
  { label: "PDF Designer", href: "/pdf-designer", icon: FileText, enabled: false },
  { label: "Bookings", href: "/bookings", icon: CalendarCheck, enabled: false },
  {
    label: "Administration",
    href: "/admin",
    icon: Settings,
    enabled: true,
    roles: ["admin"],
    children: [{ label: "Users", href: "/admin/users", enabled: true, roles: ["admin"] }],
  },
];

function allowed(item: NavItem, role?: RoleCode) {
  return item.enabled && (!item.roles || (role !== undefined && item.roles.includes(role)));
}

/** Only implemented modules the current role may use are shown. Sections with no visible children are dropped. */
export function visibleNavigation(role?: RoleCode, items: NavItem[] = NAVIGATION): NavItem[] {
  return items
    .filter((item) => allowed(item, role))
    .map((item) => ({ ...item, children: item.children?.filter((c) => allowed(c, role)) }))
    .filter((item) => !item.children || item.children.length > 0);
}
