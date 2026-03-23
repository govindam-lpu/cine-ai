"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { initials } from "@/lib/utils";
import { useUserStore } from "@/stores/userStore";

const nav = [
  { href: "/recommendations", label: "Home" },
  { href: "/taste", label: "Taste DNA" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/compatibility", label: "Compatibility" },
  { href: "/settings", label: "Profile" }
];

export default function Sidebar() {
  const pathname = usePathname();
  const user = useUserStore((state) => state.user);

  return (
    <aside className="hidden w-[260px] shrink-0 border-r border-border-default bg-[rgba(20,18,16,0.88)] p-6 lg:block">
      <Link className="font-display text-2xl uppercase tracking-[0.18em] text-text-primary" href="/recommendations">
        Cinerex
      </Link>
      <div className="mt-8 panel space-y-3 p-4">
        <div className="flex h-12 w-12 items-center justify-center border border-border-accent text-sm text-text-primary">{initials(user?.letterboxd_username)}</div>
        <div>
          <p className="font-display text-xl text-text-primary">@{user?.letterboxd_username ?? "guest"}</p>
          <p className="text-sm text-text-secondary">{user?.sync_status ?? "No active profile"}</p>
        </div>
      </div>
      <nav className="mt-8 space-y-2">
        {nav.map((item) => {
          const active = pathname === item.href;
          return (
            <Link key={item.href} className={`block border px-4 py-3 text-sm uppercase tracking-[0.14em] ${active ? "border-accent text-text-primary" : "border-transparent text-text-secondary hover:border-border-default"}`} href={item.href}>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
