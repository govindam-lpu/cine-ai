"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

import BottomNav from "@/components/layout/BottomNav";
import Sidebar from "@/components/layout/Sidebar";

type PageWrapperProps = {
  children: ReactNode;
};

const minimalRoutes = new Set(["/", "/onboarding"]);

export default function PageWrapper({ children }: PageWrapperProps) {
  const pathname = usePathname();
  const minimal = minimalRoutes.has(pathname);

  if (minimal) {
    return <main className="relative min-h-screen bg-bg-base text-text-primary">{children}</main>;
  }

  return (
    <div className="relative min-h-screen bg-bg-base text-text-primary lg:flex">
      <Sidebar />
      <main className="flex-1 pb-24 lg:pb-10">{children}</main>
      <BottomNav />
    </div>
  );
}
