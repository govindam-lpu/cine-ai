"use client";

export function useCompatibility() {
  return {
    ready: false,
    message:
      "Compatibility mode is in the planned backend contract, but the current backend has not implemented the endpoint yet. The frontend layout is ready for that payload."
  };
}
