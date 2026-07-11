"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";

import type { CreateUserInput, PreferredFormat } from "@/types/user";

type UsernameInputProps = {
  initialUsername?: string;
  loading?: boolean;
  onSubmit: (payload: CreateUserInput) => Promise<void> | void;
};

export default function UsernameInput({ initialUsername = "", loading = false, onSubmit }: UsernameInputProps) {
  const [letterboxd, setLetterboxd] = useState(initialUsername);
  const [countryCode, setCountryCode] = useState("US");
  const [preferredFormat, setPreferredFormat] = useState<PreferredFormat>("both");

  return (
    <form
      className="panel grid gap-5 p-6 md:grid-cols-2 md:p-8"
      onSubmit={async (event) => {
        event.preventDefault();
        await onSubmit({
          letterboxd_username: letterboxd.trim(),
          country_code: countryCode.trim().toUpperCase(),
          preferred_format: preferredFormat
        });
      }}
    >
      <div className="space-y-2 md:col-span-2">
        <p className="eyebrow">Step 1 / Connect</p>
        <h2 className="font-display text-4xl text-text-primary">Start with your public profile</h2>
        <p className="max-w-2xl text-sm text-text-secondary">Your public Letterboxd profile is all we need. No password, no account.</p>
      </div>
      <label className="space-y-2 md:col-span-2">
        <span className="text-xs uppercase tracking-[0.18em] text-text-muted">Letterboxd</span>
        <input className="input-base" onChange={(event) => setLetterboxd(event.target.value)} placeholder="e.g. karstenrunquist" required value={letterboxd} />
      </label>
      <label className="space-y-2">
        <span className="text-xs uppercase tracking-[0.18em] text-text-muted">Country</span>
        <input className="input-base" maxLength={2} onChange={(event) => setCountryCode(event.target.value)} placeholder="US" value={countryCode} />
      </label>
      <fieldset className="space-y-2 md:col-span-2">
        <legend className="text-xs uppercase tracking-[0.18em] text-text-muted">Preferred format</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {(["films", "shows", "both"] as const).map((option) => (
            <label key={option} className={`rounded-[6px] border px-3 py-3 text-center text-sm uppercase tracking-[0.12em] ${preferredFormat === option ? "border-accent bg-[rgba(243,201,79,0.08)] text-text-primary" : "border-border-default text-text-secondary"}`}>
              <input checked={preferredFormat === option} className="sr-only" name="preferred_format" onChange={() => setPreferredFormat(option)} type="radio" />
              {option}
            </label>
          ))}
        </div>
      </fieldset>
      <button className="button-primary w-fit gap-2" disabled={loading} type="submit">
        {loading ? "Connecting..." : "Build my profile"}
        <ArrowRight size={16} />
      </button>
    </form>
  );
}
