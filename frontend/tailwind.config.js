/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-void": "var(--bg-void)",
        "bg-base": "var(--bg-base)",
        "bg-surface": "var(--bg-surface)",
        "bg-elevated": "var(--bg-elevated)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
        "text-muted": "var(--text-muted)",
        accent: "var(--accent)",
        "accent-dim": "var(--accent-dim)",
        cyan: "var(--cyan)",
        rose: "var(--rose)",
        positive: "var(--positive)",
        warning: "var(--warning)",
        negative: "var(--negative)",
        "border-subtle": "var(--border-subtle)",
        "border-default": "var(--border-default)"
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"]
      }
      // NOTE: the archive's `spacing` override mapped to undefined --space-* vars (they were
      // never declared in globals.css), which would break every default spacing utility.
      // Dropped here; Tailwind's default spacing scale is used until the Phase 7 design pass.
    }
  },
  plugins: []
};
