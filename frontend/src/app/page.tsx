import UploadDoor from "@/components/UploadDoor";

// The door: one upload control + optional handle. No feature-card scaffolding, no "coming soon".
export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-10 px-6 py-16">
      <div className="space-y-5">
        <p className="eyebrow">Taste-based film recommendations</p>
        <h1 className="font-display text-5xl leading-[0.95] text-text-primary md:text-6xl">Cinerex</h1>
        <p className="max-w-xl text-lg leading-8 text-text-secondary">
          Upload your Letterboxd export. Get a statistical portrait of yourself as a viewer and eight
          films with a real, specific reason attached to each. No account, no scraping.
        </p>
      </div>

      <UploadDoor />

      <p className="font-mono text-xs text-text-muted">
        Your watch history stays on Letterboxd. We read the export you hand us and nothing else.
      </p>
    </main>
  );
}
