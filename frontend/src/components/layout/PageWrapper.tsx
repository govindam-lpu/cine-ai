import type { ReactNode } from "react";

type PageWrapperProps = {
  children: ReactNode;
};

export default function PageWrapper({ children }: PageWrapperProps) {
  return <main className="relative min-h-screen bg-bg-base text-text-primary">{children}</main>;
}
