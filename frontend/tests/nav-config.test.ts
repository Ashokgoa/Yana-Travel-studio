import { describe, expect, it } from "vitest";
import { NAVIGATION, visibleNavigation, type NavItem } from "@/features/navigation/nav-config";

describe("visibleNavigation", () => {
  it("hides modules that are not implemented yet", () => {
    const labels = visibleNavigation().map((i) => i.label);
    expect(labels).toContain("Dashboard");
    expect(labels).not.toContain("PDF Designer");
  });

  it("hides disabled children of an enabled module", () => {
    const items: NavItem[] = [
      { label: "CRM", href: "/crm", enabled: true, children: [
        { label: "Agents", href: "/crm/agents", enabled: true },
        { label: "Customers", href: "/crm/customers", enabled: false },
      ] },
    ];
    expect(visibleNavigation(items)[0].children?.map((c) => c.label)).toEqual(["Agents"]);
  });

  it("defines every PRD sidebar module in order", () => {
    expect(NAVIGATION.map((i) => i.label)).toEqual([
      "Dashboard", "CRM", "Itinerary Builder", "Destination Inventory", "Suppliers",
      "Pricing & Costing", "PDF Designer", "Bookings", "Administration",
    ]);
  });
});
