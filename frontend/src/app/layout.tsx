import type { Metadata } from "next";
import type { ReactNode } from "react";

import PageWrapper from "@/components/layout/PageWrapper";

import "./globals.css";

export const metadata: Metadata = {
  title: "Cinerex"
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <PageWrapper>{children}</PageWrapper>
      </body>
    </html>
  );
}
