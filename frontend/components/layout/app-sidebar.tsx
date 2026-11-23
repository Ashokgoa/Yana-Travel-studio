"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useAuth } from "@/features/auth/auth-provider";
import { visibleNavigation } from "@/features/navigation/nav-config";
import { cn } from "@/lib/utils";

export function isActivePath(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

const itemClass =
  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors " +
  "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring";

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const items = visibleNavigation(user?.role.code);

  return (
    <nav aria-label="Main" className="flex flex-col gap-1 px-3">
      {items.map((item) => {
        const Icon = item.icon;
        if (item.children?.length) {
          // Section heading with sub-pages (the parent itself has no page).
          return (
            <div key={item.href} className="mt-3">
              <p className="flex items-center gap-3 px-3 pb-1 text-[11px] font-semibold tracking-[0.14em] text-sidebar-foreground/50 uppercase">
                {Icon && <Icon className="size-3.5" aria-hidden />}
                {item.label}
              </p>
              {item.children.map((child) => {
                const active = isActivePath(pathname, child.href);
                return (
                  <Link
                    key={child.href}
                    href={child.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(itemClass, "pl-9", active && "bg-sidebar-accent text-sidebar-accent-foreground")}
                  >
                    {child.label}
                    {active && <span className="ml-auto size-1.5 rounded-full bg-sidebar-primary" aria-hidden />}
                  </Link>
                );
              })}
            </div>
          );
        }
        const active = isActivePath(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(itemClass, active && "bg-sidebar-accent text-sidebar-accent-foreground")}
          >
            {Icon && <Icon className={cn("size-4", active && "text-sidebar-primary")} aria-hidden />}
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function SidebarBrand() {
  // Text wordmark only. The official YANA DMC logo is uploaded by an administrator
  // (later phase); we never recreate the company logo.
  return (
    <div className="px-6 pt-7 pb-5">
      <p className="font-heading text-xl font-semibold tracking-wide text-sidebar-accent-foreground">YANA</p>
      <p className="text-[11px] font-medium tracking-[0.2em] text-sidebar-primary uppercase">Travel Studio</p>
    </div>
  );
}

export function SidebarUser() {
  const { user, logout } = useAuth();
  const router = useRouter();
  if (!user) return null;
  const initials = user.full_name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="m-3 flex items-center gap-3 rounded-xl bg-sidebar-accent/60 p-3">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-xs font-semibold text-sidebar-primary-foreground">
        {initials}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-sidebar-accent-foreground">{user.full_name}</p>
        <p className="truncate text-xs text-sidebar-foreground/60">{user.role.name}</p>
      </div>
      <button
        type="button"
        onClick={async () => {
          await logout();
          router.replace("/login");
        }}
        className="rounded-md p-2 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:outline-none"
        aria-label="Sign out"
        title="Sign out"
      >
        <LogOut className="size-4" />
      </button>
    </div>
  );
}

export function AppSidebar() {
  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col overflow-y-auto bg-sidebar lg:flex">
      <SidebarBrand />
      <SidebarNav />
      <div className="mt-auto">
        <SidebarUser />
      </div>
    </aside>
  );
}
