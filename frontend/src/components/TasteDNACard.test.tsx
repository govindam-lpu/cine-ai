import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import TasteDNACard from "./TasteDNACard";
import { sampleEvidence } from "@/lib/fixtures";

describe("TasteDNACard", () => {
  it("leads with the prose summary and shows interpreted stats", () => {
    render(
      <TasteDNACard
        summary="You are drawn to slow, serious films from the 1970s."
        evidence={sampleEvidence}
        displayName="Ada"
        handle="ada"
      />,
    );
    expect(screen.getByText(/slow, serious films from the 1970s/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ada" })).toBeInTheDocument();
    // obscurity -0.5 → seeks the obscure; contrarianism 0.4 → agrees with critics
    expect(screen.getByText(/seeks the obscure/i)).toBeInTheDocument();
    expect(screen.getByText(/agrees with critics/i)).toBeInTheDocument();
    expect(screen.getByText("Andrei Tarkovsky", { exact: false })).toBeInTheDocument();
  });

  it("renders without a summary (writer-degraded profile)", () => {
    render(<TasteDNACard summary={null} evidence={sampleEvidence} displayName={null} handle="guest-1" />);
    expect(screen.getByRole("heading", { name: "guest-1" })).toBeInTheDocument();
  });
});
