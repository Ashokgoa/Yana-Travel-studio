"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { visibleNavigation } from "@/features/navigation/nav-config";
import { cn } from "@/lib/utils";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const items = visibleNavigation();

  return (
    <nav aria-label="Main" className="flex flex-col gap-1 px-3">
      {items.map((item) => {
        const Icon = item.icon;
        const active = isActive(pathname, item.href);
        return (
          <div key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                active && "bg-sidebar-accent text-sidebar-accent-foreground",
              )}
            >
              {Icon && <Icon className={cn("size-4", active && "text-sidebar-primary")} aria-hidden />}
              {item.label}
            </Link>
            {item.children && item.children.length > 0 && (
              <div className="ml-7 mt-1 flex flex-col border-l border-sidebar-border pl-3">
                {item.children.map((child) => (
                  <Link
                    key={child.href}
                    href={child.href}
                    onClick={onNavigate}
                    aria-current={isActive(pathname, child.href) ? "page" : undefined}
                    className={cn(
                      "rounded-md px-2 py-1.5 text-sm text-sidebar-foreground/70 hover:text-sidebar-accent-foreground",
                      isActive(pathname, child.href) && "text-sidebar-primary",
                    )}
                  >
                    {child.label}
                  </Link>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}

export function SidebarBrand() {
  // Text wordmark only. The official YANA DMC logo is uploaded by an administrator
  // (Phase 2 / PDF Designer) — we never recreate the company logo.
  return (
    <div className="px-6 pb-6 pt-7">
      <p className="font-heading text-xl font-semibold tracking-wide text-sidebar-accent-foreground">YANA</p>
      <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-sidebar-primary">Travel Studio</p>
    </div>
  );
}

export function AppSidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col bg-sidebar lg:flex">
      <SidebarBrand />
      <SidebarNav />
      <div className="mt-auto px-6 py-5 text-xs text-sidebar-foreground/50">YANA DMC · Local edition</div>
    </aside>
  );
}
