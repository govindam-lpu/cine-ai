import type { Metadata } from "next";

import ProfileClient from "@/components/ProfileClient";

// The URL exposes a generated inference about a person — noindex is the v1 minimum (PLAN.md Risks).
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function ProfilePage({ params }: { params: { handle: string } }) {
  return <ProfileClient handle={decodeURIComponent(params.handle)} />;
}
