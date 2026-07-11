import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cinerex",
  description: "A taste-based film recommender.",
  // The profile route exposes a generated inference about a person (see docs/PLAN.md Risks).
  // noindex is the v1 minimum; kept site-wide here and enforced per-route in later phases.
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
