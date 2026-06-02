"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight } from "lucide-react";

export default function UsernameGate() {
  const router = useRouter();
  const [username, setUsername] = useState("");

  return (
    <form
      className="flex w-full max-w-2xl flex-col gap-3 sm:flex-row"
      onSubmit={(event) => {
        event.preventDefault();
        const query = username.trim() ? `?username=${encodeURIComponent(username.trim())}` : "";
        router.push(`/onboarding${query}`);
      }}
    >
      <input
        aria-label="Letterboxd username"
        className="min-h-14 flex-1 rounded-[6px] border border-border-default bg-[rgba(7,9,12,0.64)] px-5 text-base text-text-primary outline-none transition-colors placeholder:text-text-muted focus:border-accent"
        name="letterboxdUsername"
        onChange={(event) => setUsername(event.target.value)}
        placeholder="Enter your Letterboxd username"
        style={{ borderBottomColor: "var(--border-default)", color: "var(--text-primary)" }}
        type="text"
        value={username}
      />
      <button className="button-primary min-h-14 gap-2 whitespace-nowrap" type="submit">
        Build Profile
        <ArrowRight size={16} />
      </button>
    </form>
  );
}
