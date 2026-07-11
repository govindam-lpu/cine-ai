import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import RecommendationCard from "./RecommendationCard";
import { sampleRec } from "@/lib/fixtures";

describe("RecommendationCard", () => {
  it("renders the reason as the body — it is the card", () => {
    render(<RecommendationCard rec={sampleRec} />);
    expect(screen.getByText(/slow, historical drama you rate highest/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Schindler's List/i })).toBeInTheDocument();
    expect(screen.getByText("1993")).toBeInTheDocument();
  });

  it("shows specific signal chips but not the generic similarity one", () => {
    render(<RecommendationCard rec={sampleRec} />);
    expect(screen.getByText("Steven Spielberg")).toBeInTheDocument();
    expect(screen.getByText("Drama")).toBeInTheDocument();
    expect(screen.queryByText(/similarity/i)).not.toBeInTheDocument();
  });

  it("flags at-capacity when prose generation is paused", () => {
    render(<RecommendationCard rec={{ ...sampleRec, at_capacity: true }} />);
    expect(screen.getByText(/AI paused/i)).toBeInTheDocument();
  });
});
