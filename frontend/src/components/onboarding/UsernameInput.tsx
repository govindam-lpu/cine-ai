"use client";

import { useState } from "react";

import type { CreateUserInput, PreferredFormat } from "@/types/user";

type UsernameInputProps = {
  initialUsername?: string;
  loading?: boolean;
  onSubmit: (payload: CreateUserInput) => Promise<void> | void;
};

export default function UsernameInput({ initialUsername = "", loading = false, onSubmit }: UsernameInputProps) {
  const [letterboxd, setLetterboxd] = useState(initialUsername);
  const [serializd, setSerializd] = useState("");
  const [countryCode, setCountryCode] = useState("US");
  const [preferredFormat, setPreferredFormat] = useState<PreferredFormat>("both");

  return (
    <form
      className="panel grid gap-5 p-6 md:grid-cols-2"
      onSubmit={async (event) => {
        event.preventDefault();
        await onSubmit({
          letterboxd_username: letterboxd.trim(),
          serializd_username: serializd.trim() || undefined,
          country_code: countryCode.trim().toUpperCase(),
          preferred_format: preferredFormat
        });
      }}
    >
      <div className="space-y-2 md:col-span-2">
        <p className="text-xs uppercase tracking-[0.2em] text-text-muted">Step 1 · Connect</p>
        <h2 className="font-display text-3xl text-text-primary">Start with your Letterboxd username</h2>
        <p className="max-w-2xl text-sm text-text-secondary">This is the only required input for the current backend. Serializd is optional and remains Phase 2 in the API.</p>
      </div>
      <label className="space-y-2 md:col-span-2">
        <span className="text-xs uppercase tracking-[0.18em] text-text-muted">Letterboxd</span>
        <input className="input-base" onChange={(event) => setLetterboxd(event.target.value)} placeholder="e.g. karstenrunquist" required value={letterboxd} />
      </label>
      <label className="space-y-2">
        <span className="text-xs uppercase tracking-[0.18em] text-text-muted">Serializd (optional)</span>
        <input className="input-base" onChange={(event) => setSerializd(event.target.value)} placeholder="Optional for now" value={serializd} />
      </label>
      <label className="space-y-2">
        <span className="text-xs uppercase tracking-[0.18em] text-text-muted">Country</span>
        <input className="input-base" maxLength={2} onChange={(event) => setCountryCode(event.target.value)} placeholder="US" value={countryCode} />
      </label>
      <fieldset className="space-y-2 md:col-span-2">
        <legend className="text-xs uppercase tracking-[0.18em] text-text-muted">Preferred format</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {(["films", "shows", "both"] as const).map((option) => (
            <label key={option} className={`border px-3 py-3 text-sm uppercase tracking-[0.12em] ${preferredFormat === option ? "border-accent text-text-primary" : "border-border-default text-text-secondary"}`}>
              <input checked={preferredFormat === option} className="sr-only" name="preferred_format" onChange={() => setPreferredFormat(option)} type="radio" />
              {option}
            </label>
          ))}
        </div>
      </fieldset>
      <button className="button-primary w-fit" disabled={loading} type="submit">
        {loading ? "Connecting…" : "Build my profile"}
      </button>
    </form>
  );
}
