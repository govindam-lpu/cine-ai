import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import Home from "./page";

describe("Home page (the door)", () => {
  it("renders the product pitch and the upload control", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "Cinerex" })).toBeInTheDocument();
    expect(screen.getByLabelText(/upload your letterboxd export/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /read my taste/i })).toBeInTheDocument();
  });
});
