import { describe, expect, it } from "vitest";
import { NAVIGATION, visibleNavigation, type NavItem } from "@/features/navigation/nav-config";

describe("visibleNavigation", () => {
  it("hides modules that are not implemented yet", () => {
    const labels = visibleNavigation("planner").map((i) => i.label);
    expect(labels).toContain("Dashboard");
    expect(labels).toContain("CRM");
    expect(labels).not.toContain("PDF Designer");
  });

  it("shows Administration only to admins", () => {
    expect(visibleNavigation("admin").map((i) => i.label)).toContain("Administration");
    expect(visibleNavigation("planner").map((i) => i.label)).not.toContain("Administration");
    expect(visibleNavigation(undefined).map((i) => i.label)).not.toContain("Administration");
  });

  it("shows the destination inventory pages and suppliers", () => {
    const visible = visibleNavigation("planner");
    expect(visible.find((i) => i.label === "Destination Inventory")?.children?.map((c) => c.label)).toEqual([
      "Countries", "Cities", "Sightseeing", "Hotels", "Restaurants", "Transportation",
    ]);
    expect(visible.map((i) => i.label)).toContain("Suppliers");
  });

  it("shows every CRM page", () => {
    const crm = visibleNavigation("planner").find((i) => i.label === "CRM");
    expect(crm?.children?.map((c) => c.label)).toEqual(["Travel Agents", "Customers", "Enquiries"]);
  });

  it("hides disabled children and drops sections left empty", () => {
    const items: NavItem[] = [
      {
        label: "CRM", href: "/crm", enabled: true, children: [
          { label: "Agents", href: "/crm/agents", enabled: true },
          { label: "Customers", href: "/crm/customers", enabled: false },
        ],
      },
      { label: "Empty", href: "/e", enabled: true, children: [{ label: "X", href: "/e/x", enabled: false }] },
    ];
    const visible = visibleNavigation("planner", items);
    expect(visible.map((i) => i.label)).toEqual(["CRM"]);
    expect(visible[0].children?.map((c) => c.label)).toEqual(["Agents"]);
  });

  it("defines every PRD sidebar module in order", () => {
    expect(NAVIGATION.map((i) => i.label)).toEqual([
      "Dashboard", "CRM", "Itinerary Builder", "Destination Inventory", "Suppliers",
      "Pricing & Costing", "PDF Designer", "Bookings", "Administration",
    ]);
  });
});
