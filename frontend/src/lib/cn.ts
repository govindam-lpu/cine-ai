import { clsx, type ClassValue } from "clsx";

/** Conditionally join class names. Thin wrapper over clsx used across components. */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
