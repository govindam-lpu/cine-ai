// Registers jest-dom matchers (toBeInTheDocument, etc.) on Vitest's expect, and their types.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// globals:false → testing-library's auto-cleanup isn't registered; do it explicitly so the DOM
// doesn't accumulate across tests in the same file.
afterEach(() => cleanup());
