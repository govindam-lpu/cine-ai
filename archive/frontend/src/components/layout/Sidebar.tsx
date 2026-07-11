"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Dna, Settings } from "lucide-react";

import { initials } from "@/lib/utils";
import { useUserStore } from "@/stores/userStore";

const nav = [
  { href: "/recommendations", label: "Home", icon: Compass },
  { href: "/taste", label: "Taste DNA", icon: Dna },
  { href: "/settings", label: "Profile", icon: Settings }
];

export default function Sidebar() {
  const pathname = usePathname();
  const user = useUserStore((state) => state.user);

  return (
    <aside className="hidden w-[280px] shrink-0 border-r border-border-default bg-[rgba(7,9,12,0.82)] p-6 backdrop-blur-xl lg:block">
      <Link className="font-display text-2xl uppercase tracking-[0.18em] text-text-primary" href="/recommendations">
        Cinerex
      </Link>
      <div className="mt-8 panel space-y-3 p-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-[6px] border border-border-accent bg-[rgba(243,201,79,0.08)] text-sm text-text-primary">{initials(user?.letterboxd_username)}</div>
        <div>
          <p className="font-display text-xl text-text-primary">@{user?.letterboxd_username ?? "guest"}</p>
          <p className="text-sm capitalize text-text-secondary">{user?.sync_status ?? "No active profile"}</p>
        </div>
      </div>
      <nav className="mt-8 space-y-2">
        {nav.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link key={item.href} className={`flex items-center gap-3 rounded-[6px] border px-4 py-3 text-sm uppercase tracking-[0.14em] ${active ? "border-accent bg-[rgba(243,201,79,0.08)] text-text-primary" : "border-transparent text-text-secondary hover:border-border-default hover:bg-[rgba(245,241,234,0.03)]"}`} href={item.href}>
              <Icon size={17} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
