import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import Home from "./page";

describe("Home page", () => {
  it("renders the product one-liner", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: /taste-based film recommender/i }),
    ).toBeInTheDocument();
  });
});
