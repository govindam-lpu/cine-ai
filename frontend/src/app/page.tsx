export default function HomePage() {
  return (
    <section className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-12">
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at center, var(--accent-glow) 0%, transparent 48%)"
        }}
      />
      <div className="relative z-10 flex w-full max-w-2xl flex-col items-center gap-6 text-center">
        <h1
          className="font-display text-5xl uppercase sm:text-7xl"
          style={{
            color: "var(--text-primary)",
            letterSpacing: "0.15em",
            lineHeight: 1.15
          }}
        >
          CINEREX
        </h1>
        <p
          className="max-w-xl text-lg sm:text-xl"
          style={{ color: "var(--text-secondary)" }}
        >
          Film recommendations that know you.
        </p>
        <form className="mt-4 flex w-full max-w-xl flex-col gap-4">
          <input
            aria-label="Letterboxd username"
            type="text"
            name="letterboxdUsername"
            placeholder="Enter your Letterboxd username"
            className="w-full border-0 border-b bg-transparent px-0 py-4 text-center outline-none transition-colors placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
            style={{
              borderBottomColor: "var(--border-default)",
              color: "var(--text-primary)",
              fontSize: "var(--text-md)"
            }}
          />
          <button
            type="submit"
            className="mx-auto inline-flex items-center justify-center border px-6 py-3 uppercase tracking-[0.12em] transition-transform duration-200 hover:-translate-y-px"
            style={{
              backgroundColor: "var(--accent)",
              borderColor: "var(--border-accent)",
              color: "var(--text-inverse)"
            }}
          >
            Build My Profile
          </button>
        </form>
      </div>
    </section>
  );
}
