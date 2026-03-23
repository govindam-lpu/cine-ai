"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/recommendations", label: "Home" },
  { href: "/taste", label: "Taste" },
  { href: "/compatibility", label: "Match" },
  { href: "/settings", label: "Profile" }
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 grid grid-cols-4 border-t border-border-default bg-[rgba(20,18,16,0.96)] lg:hidden">
      {nav.map((item) => (
        <Link key={item.href} className={`px-3 py-4 text-center text-[11px] uppercase tracking-[0.16em] ${pathname === item.href ? "text-accent" : "text-text-secondary"}`} href={item.href}>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
