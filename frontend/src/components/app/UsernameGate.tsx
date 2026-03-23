"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function UsernameGate() {
  const router = useRouter();
  const [username, setUsername] = useState("");

  return (
    <form
      className="flex w-full max-w-xl flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        const query = username.trim() ? `?username=${encodeURIComponent(username.trim())}` : "";
        router.push(`/onboarding${query}`);
      }}
    >
      <input
        aria-label="Letterboxd username"
        className="w-full border-0 border-b bg-transparent px-0 py-4 text-center text-lg outline-none transition-colors placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
        name="letterboxdUsername"
        onChange={(event) => setUsername(event.target.value)}
        placeholder="Enter your Letterboxd username"
        style={{ borderBottomColor: "var(--border-default)", color: "var(--text-primary)" }}
        type="text"
        value={username}
      />
      <button className="button-primary mx-auto" type="submit">
        Build My Profile
      </button>
    </form>
  );
}
