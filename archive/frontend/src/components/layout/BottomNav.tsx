"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Dna, Settings } from "lucide-react";

const nav = [
  { href: "/recommendations", label: "Home", icon: Compass },
  { href: "/taste", label: "Taste", icon: Dna },
  { href: "/settings", label: "Profile", icon: Settings }
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 grid grid-cols-3 border-t border-border-default bg-[rgba(7,9,12,0.96)] backdrop-blur-xl lg:hidden">
      {nav.map((item) => {
        const Icon = item.icon;
        return (
          <Link key={item.href} className={`flex flex-col items-center gap-1 px-3 py-3 text-center text-[10px] uppercase tracking-[0.14em] ${pathname === item.href ? "text-accent" : "text-text-secondary"}`} href={item.href}>
            <Icon size={17} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
