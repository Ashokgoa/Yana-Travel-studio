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

export type NavItem = {
  label: string;
  href: string;
  icon?: LucideIcon;
  /** Modules are hidden until implemented (PRD 5.2). Flip to true when a phase ships. */
  enabled: boolean;
  children?: NavItem[];
};

export const NAVIGATION: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, enabled: true },
  {
    label: "CRM",
    href: "/crm",
    icon: Users,
    enabled: false, // Phase 1
    children: [
      { label: "Travel Agents", href: "/crm/agents", enabled: false },
      { label: "Customers", href: "/crm/customers", enabled: false },
      { label: "Enquiries", href: "/crm/enquiries", enabled: false },
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
    enabled: false, // Phase 2
    children: [
      { label: "Countries", href: "/inventory/countries", enabled: false },
      { label: "Cities", href: "/inventory/cities", enabled: false },
      { label: "Sightseeing", href: "/inventory/sightseeing", enabled: false },
      { label: "Hotels", href: "/inventory/hotels", enabled: false },
      { label: "Restaurants", href: "/inventory/restaurants", enabled: false },
      { label: "Transportation", href: "/inventory/transportation", enabled: false },
    ],
  },
  { label: "Suppliers", href: "/suppliers", icon: Building2, enabled: false },
  { label: "Pricing & Costing", href: "/pricing", icon: Calculator, enabled: false },
  { label: "PDF Designer", href: "/pdf-designer", icon: FileText, enabled: false },
  { label: "Bookings", href: "/bookings", icon: CalendarCheck, enabled: false },
  { label: "Administration", href: "/admin", icon: Settings, enabled: false },
];

/** Only implemented modules (and their implemented children) are shown. */
export function visibleNavigation(items: NavItem[] = NAVIGATION): NavItem[] {
  return items
    .filter((item) => item.enabled)
    .map((item) => ({ ...item, children: item.children?.filter((c) => c.enabled) }));
}
