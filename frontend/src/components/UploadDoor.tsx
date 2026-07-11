"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { ApiError, uploadExport } from "@/lib/api";
import { cn } from "@/lib/cn";

export default function UploadDoor() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [handle, setHandle] = useState("");
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    try {
      const { handle: resolved } = await uploadExport(file, handle.trim() || undefined);
      router.push(`/u/${encodeURIComponent(resolved)}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      setBusy(false);
    }
  }

  function pick(f: File | undefined) {
    if (!f) return;
    setFile(f);
    setError(null);
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files?.[0]);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload your Letterboxd export"
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-[8px] border border-dashed p-8 text-center transition-colors",
          dragging ? "border-border-accent bg-[var(--accent-glow)]" : "border-border-default",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".zip,.csv"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0] ?? undefined)}
        />
        <p className="font-display text-xl text-text-primary">
          {file ? file.name : "Drop your Letterboxd export"}
        </p>
        <p className="text-sm text-text-muted">
          {file ? "Ready to read your taste" : "the .zip from Settings → Import & Export → Export Your Data"}
        </p>
      </div>

      <input
        className="input-base"
        placeholder="Optional handle (leave blank for a random one)"
        value={handle}
        onChange={(e) => setHandle(e.target.value)}
        aria-label="Optional handle"
      />

      {error ? <p className="text-sm text-negative">{error}</p> : null}

      <button className="button-primary w-full" onClick={submit} disabled={!file || busy}>
        {busy ? "Uploading…" : "Read my taste"}
      </button>
    </div>
  );
}
