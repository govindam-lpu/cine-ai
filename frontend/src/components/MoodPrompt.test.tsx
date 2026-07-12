import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import MoodPrompt from "./MoodPrompt";

describe("MoodPrompt", () => {
  it("submits typed free text on Find", () => {
    const onSubmit = vi.fn();
    render(<MoodPrompt value="" onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/mood/i), {
      target: { value: "a slow, melancholic sci-fi" },
    });
    fireEvent.click(screen.getByRole("button", { name: /find/i }));
    expect(onSubmit).toHaveBeenCalledWith("a slow, melancholic sci-fi");
  });

  it("submits immediately when a quick-fill suggestion is tapped", () => {
    const onSubmit = vi.fn();
    render(<MoodPrompt value="" onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Dark" }));
    expect(onSubmit).toHaveBeenCalledWith("Dark");
  });
});
